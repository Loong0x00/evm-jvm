#!/usr/bin/env python3
"""Fail-closed replay orchestration for the frozen P34 public Go transport.

This controller never interprets Java/class/ZIP contents. It passes explicitly
provided inputs to the pinned public EVM transport and only inspects its
canonical public receipts, opaque durable Head, and SHA-256 checkpoint files.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MISSING_SELECTOR = bytes.fromhex("555db429")
MISSING_SIGNATURE = "MCEntryMissingClass(uint256,uint256,bytes)"
STATE_SCHEMA = 1
TERMINAL_LIFECYCLES = {2, 3}


class ControllerError(RuntimeError):
    """A fail-closed configuration, transport, or evidence failure."""


class IntegrityError(ControllerError):
    """Evidence contradicts the frozen EVM/transport contract."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ControllerError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def read_json(path: Path, limit: int = 4 * 1024 * 1024) -> Any:
    st = path.lstat()
    if not path.is_file() or path.is_symlink() or st.st_size < 0 or st.st_size > limit:
        raise ControllerError(f"not a bounded regular file: {path}")
    raw = path.read_bytes()
    try:
        return json.loads(raw, object_pairs_hook=_strict_object,
                          parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ControllerError(f"invalid JSON {path}: {exc}") from exc


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path, limit: int | None = None) -> str:
    st = path.lstat()
    if not path.is_file() or path.is_symlink() or (limit is not None and st.st_size > limit):
        raise ControllerError(f"not an allowed regular file: {path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _hex32(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]{64}", value):
        raise ControllerError(f"{label} must be a 32-byte 0x-prefixed hex value")
    return value.lower()


def _norm_hash(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]{64}", value):
        raise IntegrityError("Head contains malformed bytes32")
    return value.lower()


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise IntegrityError(f"{label} is not a nonnegative integer")
    return value


def _word(n: int) -> bytes:
    if n < 0 or n >= 1 << 256:
        raise ValueError("ABI uint256 range")
    return n.to_bytes(32, "big")


def encode_missing_class(site: int, context: int, name: bytes) -> bytes:
    """Test helper implementing the single canonical ABI layout."""
    pad = (-len(name)) % 32
    body = _word(site) + _word(context) + _word(96) + _word(len(name)) + name + bytes(pad)
    return MISSING_SELECTOR + body


def decode_canonical_missing_class(raw: bytes) -> tuple[int, int, bytes] | None:
    """Decode exactly selector 555db429 and its sole canonical dynamic tail."""
    if len(raw) < 4 or raw[:4] != MISSING_SELECTOR:
        return None
    args = raw[4:]
    if len(args) < 128 or len(args) % 32:
        return None
    site = int.from_bytes(args[0:32], "big")
    context = int.from_bytes(args[32:64], "big")
    if int.from_bytes(args[64:96], "big") != 96:
        return None
    n = int.from_bytes(args[96:128], "big")
    padded = (n + 31) // 32 * 32
    if 128 + padded != len(args):
        return None
    name = args[128:128 + n]
    if any(args[128 + n:]):
        return None
    if not name or b"\x00" in name:
        return None
    try:
        name.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return None
    return site, context, name


def canonical_head(head: dict[str, Any]) -> dict[str, Any]:
    """Fields that define the EVM/package/checkpoint/counter state, excluding host time/PIDs."""
    required_hashes = ("trieRoot", "engineCodeHash", "coordinatorCodeHash", "packageRoot",
                       "instanceId", "checkpointRoot", "machineRoot", "vfsRoot")
    out: dict[str, Any] = {k: _norm_hash(head.get(k)) for k in required_hashes}
    for key in ("engine", "coordinator"):
        value = head.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]{40}", value):
            raise IntegrityError(f"Head contains malformed {key}")
        out[key] = value.lower()
    for key in ("engineNonce", "epoch", "lifecycle", "outcome", "result", "javaKind", "javaRef",
                "jvmSteps", "internalSteps", "quantum", "slices", "totalClassBytes"):
        out[key] = _integer(head.get(key), f"Head.{key}")
    out["checkpointSHA256"] = head.get("checkpointSHA256")
    if not isinstance(out["checkpointSHA256"], str) or not re.fullmatch(r"[0-9a-f]{64}", out["checkpointSHA256"]):
        raise IntegrityError("Head contains malformed checkpointSHA256")
    out["javaClass"] = head.get("javaClass")
    if out["javaClass"] is None:
        out["javaClass"] = ""
    if not isinstance(out["javaClass"], str):
        raise IntegrityError("Head.javaClass is not base64 text")
    counters = head.get("counters")
    if not isinstance(counters, dict):
        raise IntegrityError("Head.counters is absent")
    for key, value in counters.items():
        if key in ("maxCallMs", "commitMs"):
            _integer(value, f"Head.counters.{key}")
        elif key == "actualDI0ReadSizes":
            if value is not None and (not isinstance(value, list) or any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in value)):
                raise IntegrityError("Head.counters.actualDI0ReadSizes is malformed")
        else:
            _integer(value, f"Head.counters.{key}")
    # Keep deterministic transport/gas/read/write counts in equivalence. Host
    # elapsed-millisecond telemetry is measured separately and varies per replay.
    out["counters"] = {k: v for k, v in counters.items() if k not in ("maxCallMs", "commitMs")}
    return out


def validate_head_pins(head: dict[str, Any], pins: dict[str, Any], package_hash: str) -> None:
    if _norm_hash(head.get("engineCodeHash")) != "0x" + pins["engine"]["runtimeKeccak256"].lower().removeprefix("0x"):
        raise IntegrityError("Head engine code hash differs from provided build pin")
    if _norm_hash(head.get("coordinatorCodeHash")) != "0x" + pins["coordinator"]["runtimeKeccak256"].lower().removeprefix("0x"):
        raise IntegrityError("Head coordinator code hash differs from provided build pin")
    if _norm_hash(head.get("packageRoot")) != package_hash:
        raise IntegrityError("Head packageRoot differs from explicit package hash")
    if head.get("engineNonce") != 0 or head.get("engine", "").lower() != pins["address"].lower():
        raise IntegrityError("Head engine address/nonce differs from provided build")
    if _integer(head.get("quantum"), "Head.quantum") <= 0:
        raise IntegrityError("Head quantum is zero")


def validate_build(build: Path, flags: argparse.Namespace) -> tuple[dict[str, Any], Path, Path]:
    pins = read_json(build / "pins.json")
    if pins.get("profile") != "MC-CHECKPOINT-2M-P34":
        raise ControllerError("provided build is not the explicitly supported P34 profile")
    for k in ("engine", "coordinator"):
        if not isinstance(pins.get(k), dict):
            raise ControllerError(f"pins.json lacks {k} code pin")
    supplied = {
        "engineRuntimeSHA256": flags.engine_runtime_sha256.lower(),
        "engineRuntimeKeccak256": flags.engine_runtime_keccak256.lower().removeprefix("0x"),
        "coordinatorRuntimeSHA256": flags.coordinator_runtime_sha256.lower(),
        "coordinatorRuntimeKeccak256": flags.coordinator_runtime_keccak256.lower().removeprefix("0x"),
    }
    expected = {
        "engineRuntimeSHA256": pins["engine"]["runtimeSHA256"].lower(),
        "engineRuntimeKeccak256": pins["engine"]["runtimeKeccak256"].lower().removeprefix("0x"),
        "coordinatorRuntimeSHA256": pins["coordinator"]["runtimeSHA256"].lower(),
        "coordinatorRuntimeKeccak256": pins["coordinator"]["runtimeKeccak256"].lower().removeprefix("0x"),
    }
    if supplied != expected:
        raise ControllerError("explicit runtime code pins differ from build/pins.json")
    if _integer(pins.get("externalLocalGas"), "pins.externalLocalGas") != flags.max_call_gas:
        raise ControllerError("--max-call-gas must equal the provided build's LOCAL call gas")
    if flags.max_call_gas <= 0:
        raise ControllerError("max-call-gas must be positive")
    if flags.wall_limit_seconds <= 0:
        raise ControllerError("wall-limit-seconds must be positive")
    if _integer(pins.get("maxCheckpointBytes"), "pins.maxCheckpointBytes") <= 0:
        raise ControllerError("invalid checkpoint cap")
    if _integer(pins.get("maxJvmSteps"), "pins.maxJvmSteps") > 65536:
        raise ControllerError("the controller will not raise the frozen P34 per-slice JVM cap")
    if _integer(pins.get("maxInternalSteps"), "pins.maxInternalSteps") > 4096:
        raise ControllerError("the controller will not raise the frozen P34 per-slice internal cap")
    if _integer(pins.get("runtimeCap"), "pins.runtimeCap") != 1048576:
        raise ControllerError("unexpected P34 runtime cap")
    if _integer(pins["engine"].get("bytes"), "pins.engine.bytes") > pins["runtimeCap"]:
        raise ControllerError("provided engine exceeds its own pinned LOCAL runtime cap")
    engine = build / "engine" / "MCEntryInterpreter.json"
    coordinator = build / "coordinator" / "MCEntryCoordinator.json"
    for path, name, runtime_sha, runtime_keccak, byte_count in (
        (engine, "engine", expected["engineRuntimeSHA256"], expected["engineRuntimeKeccak256"], pins["engine"]["bytes"]),
        (coordinator, "coordinator", expected["coordinatorRuntimeSHA256"], expected["coordinatorRuntimeKeccak256"], pins["coordinator"]["bytes"]),
    ):
        art = read_json(path, 32 * 1024 * 1024)
        code = art.get("deployedBytecode")
        if not isinstance(code, str):
            raise ControllerError(f"{name} artifact has no deployedBytecode")
        code = code.removeprefix("0x")
        if len(code) % 2:
            raise ControllerError(f"{name} deployedBytecode has odd hex length")
        try:
            raw = bytes.fromhex(code)
        except ValueError as exc:
            raise ControllerError(f"{name} deployedBytecode is not hex") from exc
        if len(raw) != byte_count or sha256(raw) != runtime_sha:
            raise ControllerError(f"{name} deployedBytecode bytes/hash differ from pins")
        code_hashes = art.get("codeHashes", {})
        if code_hashes.get("runtimeSHA256", "").lower() != runtime_sha or code_hashes.get("runtimeKeccak256", "").lower().removeprefix("0x") != runtime_keccak:
            raise ControllerError(f"{name} artifact runtime metadata differs from pins")
    engine_abi = read_json(engine, 32 * 1024 * 1024).get("abi")
    abi_error = [x for x in engine_abi if x.get("type") == "error" and x.get("name") == "MCEntryMissingClass"]
    if len(abi_error) != 1 or [x.get("type") for x in abi_error[0].get("inputs", [])] != ["uint256", "uint256", "bytes"]:
        raise ControllerError("P34 artifact MCEntryMissingClass ABI is not the frozen signature")
    if MISSING_SIGNATURE != "MCEntryMissingClass(uint256,uint256,bytes)":
        raise AssertionError("internal selector/signature mismatch")
    if flags.max_quantum is None:
        flags.max_quantum = _integer(pins["maxJvmSteps"], "pins.maxJvmSteps")
    if flags.initial_quantum is None:
        flags.initial_quantum = flags.max_quantum
    if not (1 <= flags.max_quantum <= flags.initial_quantum <= pins["maxJvmSteps"]):
        raise ControllerError("quantum must satisfy 1 <= max-quantum <= initial-quantum <= frozen P34 cap")
    return pins, coordinator, engine


def load_bindings(path: Path) -> tuple[list[str], str, bytes]:
    st = path.lstat()
    if not path.is_file() or path.is_symlink() or st.st_size < 0 or st.st_size > 1024 * 1024:
        raise ControllerError("bindings input is not a bounded regular file")
    raw = path.read_bytes()
    if len(raw) > 1024 * 1024:
        raise ControllerError("bindings input exceeds 1 MiB")
    try:
        data = json.loads(raw, object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ControllerError(f"invalid bindings JSON: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise ControllerError("bindings JSON must be {schema:1,bindings:[...],selectedResource?:...}")
    names = data.get("bindings")
    if not isinstance(names, list) or not names or len(names) > 150:
        raise ControllerError("explicit bindings must contain 1..150 names")
    for name in names:
        if not isinstance(name, str) or not name or len(name.encode("utf-8")) > 256 or "," in name or "\x00" in name:
            raise ControllerError("invalid explicit binding name")
    if len(set(names)) != len(names):
        raise ControllerError("duplicate explicit binding names")
    selected = data.get("selectedResource", "")
    if not isinstance(selected, str) or len(selected.encode("ascii", "strict")) > 256 or "," in selected or selected.startswith("/") or "\\" in selected:
        raise ControllerError("invalid selectedResource")
    return names, selected, raw


def _safe_head_bytes(world: Path) -> bytes:
    p = world / "durable-head.json"
    try:
        st = p.lstat()
    except FileNotFoundError as exc:
        raise ControllerError("world has no durable Head") from exc
    if not p.is_file() or p.is_symlink() or st.st_size <= 0 or st.st_size > 32768:
        raise IntegrityError("durable Head is not a bounded regular file")
    return p.read_bytes()


def _head_from(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw, object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"invalid durable Head JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise IntegrityError("durable Head is not an object")
    canonical_head(value)
    return value


def _report_dir(world: Path) -> Path:
    # This is the P34 transport's documented reports sibling, derived only from the explicit world path.
    return world.parent / "reports" / world.name


def _remove_or_archive(path: Path, archive_dir: Path, label: str) -> tuple[Path, str] | None:
    try:
        st = path.lstat()
    except FileNotFoundError:
        return None
    if not path.is_file() or path.is_symlink() or st.st_size > 1024 * 1024:
        raise IntegrityError(f"unexpected existing receipt shape: {path}")
    raw = path.read_bytes()
    digest = sha256(raw)
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / f"{label}-{digest[:12]}.json"
    suffix = 0
    while target.exists():
        if target.read_bytes() == raw:
            # Do not delete the only extant receipt if a prior archive already exists.
            target = archive_dir / f"{label}-{digest[:12]}-{suffix + 1}.json"
            suffix += 1
            continue
        suffix += 1
        target = archive_dir / f"{label}-{digest[:12]}-{suffix}.json"
    os.replace(path, target)
    _fsync_dir(path.parent)
    _fsync_dir(archive_dir)
    return target, digest


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = (json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    fd, temp = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(blob)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
        _fsync_dir(path.parent)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp)


def validate_atomic_refusal(receipt: dict[str, Any], head_bytes: bytes, head: dict[str, Any], max_call_gas: int) -> None:
    root = _norm_hash(head.get("trieRoot"))
    head_sha = sha256(head_bytes)
    if receipt.get("rootUnchanged") is not True or receipt.get("durableHeadUnchanged") is not True:
        raise IntegrityError("refusal receipt does not prove root and durable Head unchanged")
    if _norm_hash(receipt.get("rootBefore")) != root or _norm_hash(receipt.get("rootAfter")) != root:
        raise IntegrityError("refusal root differs from the authenticated prior EVM root")
    if receipt.get("durableHeadSHA256Before") != head_sha or receipt.get("durableHeadSHA256After") != head_sha:
        raise IntegrityError("refusal durable Head hashes do not match the byte-exact prior Head")
    epoch = _integer(head.get("epoch"), "Head.epoch")
    if receipt.get("durableHeadEpochBefore") != epoch or receipt.get("durableHeadEpochAfter") != epoch:
        raise IntegrityError("refusal durable Head epochs differ from the prior successful Head")
    if _integer(receipt.get("checkpointBytes"), "refusal.checkpointBytes") != 0:
        raise IntegrityError("a refusal returned a nonzero checkpoint byte count")
    for key in ("candidateHead", "candidateCheckpoint", "candidateRoot"):
        if receipt.get(key) != "":
            raise IntegrityError(f"refusal leaked a candidate {key}")
    if _integer(receipt.get("suppliedGas"), "refusal.suppliedGas") != max_call_gas:
        raise IntegrityError("refusal was not made with the explicitly pinned call gas")


def classify_missing_refusal(receipt: dict[str, Any], head_bytes: bytes, head: dict[str, Any], max_call_gas: int) -> str | None:
    """Return exact missing typename only after complete canonical/atomic proof."""
    validate_atomic_refusal(receipt, head_bytes, head, max_call_gas)
    revert = receipt.get("revertHex")
    if not isinstance(revert, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", revert):
        return None
    raw = bytes.fromhex(revert[2:])
    expected_selector = "0x" + raw[:4].hex() if len(raw) >= 4 else "0x"
    if receipt.get("selector") != expected_selector:
        return None
    decoded = decode_canonical_missing_class(raw)
    diagnostic = receipt.get("diagnostic")
    if decoded is None or not isinstance(diagnostic, dict):
        return None
    site, context, name = decoded
    try:
        exact_name = name.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return None
    if diagnostic.get("site") != str(site) or diagnostic.get("context") != str(context) or diagnostic.get("name") != exact_name:
        return None
    return exact_name


def _head_projection(head: dict[str, Any], pins: dict[str, Any], package_hash: str) -> dict[str, Any]:
    validate_head_pins(head, pins, package_hash)
    return canonical_head(head)


def validate_success(before: dict[str, Any], after_raw: bytes, world: Path, pins: dict[str, Any], package_hash: str,
                     q: int, report: dict[str, Any], max_call_gas: int) -> dict[str, Any]:
    after = _head_from(after_raw)
    before_c = canonical_head(before)
    after_c = _head_projection(after, pins, package_hash)
    if _integer(after.get("epoch"), "Head.epoch") != _integer(before.get("epoch"), "Head.epoch") + 1:
        raise IntegrityError("successful resume did not commit exactly one epoch")
    if after_c["trieRoot"] == before_c["trieRoot"] or after_c["checkpointSHA256"] == before_c["checkpointSHA256"]:
        raise IntegrityError("successful resume did not publish a new authenticated checkpoint/root")
    cp_size = _integer(report.get("checkpointBytes"), "slice.checkpointBytes")
    if cp_size <= 0 or cp_size > pins["maxCheckpointBytes"]:
        raise IntegrityError("successful slice checkpoint size is outside the provided P34 cap")
    cp_sha = report.get("checkpointSHA256")
    if cp_sha != after.get("checkpointSHA256"):
        raise IntegrityError("slice receipt checkpoint hash differs from durable Head")
    cp = world / "checkpoints" / f"{cp_sha}.bin"
    if sha256_file(cp, pins["maxCheckpointBytes"]) != cp_sha:
        raise IntegrityError("successful opaque checkpoint SHA256 mismatch")
    if cp.stat().st_size != cp_size:
        raise IntegrityError("successful checkpoint byte count mismatch")
    sl = report.get("slice")
    if not isinstance(sl, dict):
        raise IntegrityError("successful slice receipt lacks decoded slice")
    def sf(name: str) -> Any:
        # Frozen Go reports use ABI field json tags (lower camel case).
        if name in sl:
            return sl[name]
        cap = name[0].upper() + name[1:]
        return sl.get(cap)
    if _integer(report.get("suppliedGas"), "slice.suppliedGas") != max_call_gas:
        raise IntegrityError("successful slice used a different call gas")
    gas_used = _integer(report.get("gasUsed"), "slice.gasUsed")
    if not 0 < gas_used <= max_call_gas:
        raise IntegrityError("successful slice gas accounting is invalid")
    if _integer(report.get("elapsedMS"), "slice.elapsedMS") > pins["callWatchdogMs"]:
        raise IntegrityError("successful slice exceeds the transport's pinned call watchdog")
    epoch = _integer(after.get("epoch"), "Head.epoch")
    if _integer(sf("epoch"), "slice.epoch") != epoch:
        raise IntegrityError("successful slice epoch mismatch")
    if _integer(sf("totalJvmSteps"), "slice.totalJvmSteps") != _integer(after.get("jvmSteps"), "Head.jvmSteps"):
        raise IntegrityError("successful JVM instruction total differs from Head")
    if _integer(sf("totalInternalSteps"), "slice.totalInternalSteps") != _integer(after.get("internalSteps"), "Head.internalSteps"):
        raise IntegrityError("successful internal instruction total differs from Head")
    dj = _integer(after.get("jvmSteps"), "Head.jvmSteps") - _integer(before.get("jvmSteps"), "Head.jvmSteps")
    di = _integer(after.get("internalSteps"), "Head.internalSteps") - _integer(before.get("internalSteps"), "Head.internalSteps")
    if dj < 0 or di < 0 or dj > q or di > pins["maxInternalSteps"] or dj + di == 0:
        raise IntegrityError("successful step deltas violate the frozen quantum bounds")
    if _integer(sf("executedJvmSteps"), "slice.executedJvmSteps") != dj or _integer(sf("executedInternalSteps"), "slice.executedInternalSteps") != di:
        raise IntegrityError("slice executed-step deltas differ from durable Head")
    if _norm_hash(sf("checkpointRoot")) != _norm_hash(after.get("checkpointRoot")):
        raise IntegrityError("slice checkpoint root differs from durable Head")
    if _norm_hash(sf("machineStateRoot")) != _norm_hash(after.get("machineRoot")) or _norm_hash(sf("vfsStateRoot")) != _norm_hash(after.get("vfsRoot")):
        raise IntegrityError("slice machine/VFS root differs from durable Head")
    if _integer(sf("lifecycle"), "slice.lifecycle") != _integer(after.get("lifecycle"), "Head.lifecycle"):
        raise IntegrityError("slice lifecycle differs from durable Head")
    if _integer(sf("result"), "slice.result") != _integer(after.get("result"), "Head.result"):
        raise IntegrityError("slice guest result differs from durable Head")
    if after.get("result") != 0:
        raise IntegrityError("successful EVM slice has unexpected host result code")
    return {"epoch": epoch, "q": q, "deltaJvm": dj, "deltaInternal": di, "lifecycle": after["lifecycle"],
            "gasUsed": gas_used, "elapsedMS": report["elapsedMS"], "checkpointBytes": cp_size,
            "checkpointSHA256": cp_sha, "before": before_c, "after": after_c}


@dataclass
class Config:
    mode: str
    action: str
    driver: Path
    build: Path
    coordinator: Path
    engine: Path
    fixture: Path
    bindings_path: Path
    names: list[str]
    selected: str
    bindings_raw: bytes
    package_hash: str
    world: Path
    results: Path
    pins: dict[str, Any]
    max_call_gas: int
    wall_limit_seconds: float
    max_quantum: int
    initial_quantum: int
    max_calls: int
    continue_from: Path | None
    identity: dict[str, Any]


class Runner:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.started = time.monotonic()
        self.events: list[dict[str, Any]] = []
        self.pending: dict[str, Any] | None = None
        self.next_q = cfg.initial_quantum
        self.had_refusal = False
        self.state_path = cfg.results / "state.json"
        self.summary_path = cfg.results / "summary.json"
        self.archive_dir = cfg.results / "refusals"
        self.lock_file = cfg.world.parent / f".{cfg.world.name}.replay-controller.lock"
        self.logs_dir = cfg.results / "process-logs"
        self.state: dict[str, Any] = {}

    def _elapsed(self) -> float:
        return time.monotonic() - self.started

    def _remaining(self) -> float:
        left = self.cfg.wall_limit_seconds - self._elapsed()
        if left <= 0:
            raise TimeoutError("controller wall limit exhausted")
        return left

    def _save(self, status: str | None = None, detail: str | None = None) -> None:
        if status is not None:
            self.state["status"] = status
        if detail is not None:
            self.state["detail"] = detail
        self.state["events"] = self.events
        self.state["pending"] = self.pending
        self.state["nextQuantum"] = self.next_q
        self.state["hadRefusal"] = self.had_refusal
        self.state["elapsedSeconds"] = self._elapsed()
        self.state["lastInvocationWallLimitSeconds"] = self.cfg.wall_limit_seconds
        self.state["lastInvocationMaxCalls"] = self.cfg.max_calls
        atomic_json(self.state_path, self.state)
        if status is not None:
            atomic_json(self.summary_path, self.state)

    def _new_state(self) -> None:
        self.state = {"schema": STATE_SCHEMA, "mode": self.cfg.mode, "action": self.cfg.action,
                      "identity": self.cfg.identity, "status": "running", "events": [],
                      "pending": None, "nextQuantum": self.next_q, "hadRefusal": False,
                      "createdUTC": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "acceptanceEligible": False}
        if self.cfg.continue_from:
            prior = read_json(self.cfg.continue_from)
            self._seed_from_discovery(prior)
        self._save()

    def _seed_from_discovery(self, prior: dict[str, Any]) -> None:
        if prior.get("status") != "discovery-missing-class-not-terminal-success-not-q1-acceptance":
            raise ControllerError("--continue-from must be an authenticated nonterminal discovery stop")
        if prior.get("acceptanceEligible") is not False or prior.get("terminalGuestOutcome") is not False or prior.get("q1FrontierAcceptance") is not False:
            raise IntegrityError("discovery result carries forbidden acceptance claims")
        if prior.get("identity") != self.cfg.identity:
            raise ControllerError("continuation inputs/package/code pins differ from discovery")
        stop = prior.get("discoveryStop")
        if not isinstance(stop, dict) or not isinstance(stop.get("missingClass"), str):
            raise IntegrityError("discovery result lacks exact missing-class proof")
        q = _integer(stop.get("q"), "discoveryStop.q")
        if q <= 1 or _integer(stop.get("nextQuantum"), "discoveryStop.nextQuantum") != max(1, q // 2):
            raise IntegrityError("discovery continuation does not halve the failed quantum")
        expected_head = stop.get("lastSuccessfulHead")
        current = _head_from(_safe_head_bytes(self.cfg.world))
        current_projection = _head_projection(current, self.cfg.pins, self.cfg.package_hash)
        if current_projection != expected_head:
            raise IntegrityError("continuation world is not at the discovery's last successful same-package Head")
        if _integer(current.get("lifecycle"), "Head.lifecycle") != 1:
            raise IntegrityError("cannot continue from a terminal or non-running Head")
        events = prior.get("events")
        if not isinstance(events, list) or not any(e.get("kind") in ("start", "success") for e in events if isinstance(e, dict)):
            raise IntegrityError("discovery has no prior successful authenticated Head")
        archived = stop.get("receiptArchive")
        if not isinstance(archived, dict) or not isinstance(archived.get("path"), str):
            raise IntegrityError("discovery receipt archive pin is missing")
        archive_root = self.cfg.continue_from.parent.resolve()
        relative_receipt = Path(archived["path"])
        if relative_receipt.is_absolute() or ".." in relative_receipt.parts:
            raise IntegrityError("discovery receipt archive path is not local")
        candidate = archive_root / relative_receipt
        cursor = archive_root
        for part in relative_receipt.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise IntegrityError("discovery receipt archive contains a symlink")
        receipt_path = candidate.resolve(strict=True)
        if not receipt_path.is_relative_to(archive_root):
            raise IntegrityError("discovery receipt archive escapes its evidence directory")
        if not receipt_path.is_file() or sha256_file(receipt_path, 1024 * 1024) != archived.get("sha256"):
            raise IntegrityError("discovery refusal receipt archive failed its hash pin")
        receipt = read_json(receipt_path, 1024 * 1024)
        prior_bytes_hex = stop.get("priorHeadBytesHex")
        if not isinstance(prior_bytes_hex, str) or len(prior_bytes_hex) > 65536 or not re.fullmatch(r"(?:[0-9a-fA-F]{2})+", prior_bytes_hex):
            raise IntegrityError("discovery prior Head bytes are malformed")
        prior_bytes = bytes.fromhex(prior_bytes_hex)
        prior_head = _head_from(prior_bytes)
        if canonical_head(prior_head) != expected_head or _head_projection(prior_head, self.cfg.pins, self.cfg.package_hash) != expected_head:
            raise IntegrityError("discovery prior Head bytes differ from its canonical proof")
        raw_head = _safe_head_bytes(self.cfg.world)
        name = classify_missing_refusal(receipt, prior_bytes, prior_head, self.cfg.max_call_gas)
        if name != stop["missingClass"]:
            raise IntegrityError("discovery receipt no longer proves the recorded exact missing typename")
        # The byte-exact failed-call Head and the current same-package EVM projection
        # must agree. Verify's metadata rewrites are excluded from the projection.
        if stop.get("priorHeadSHA256") != sha256(bytes.fromhex(stop["priorHeadBytesHex"])):
            raise IntegrityError("discovery prior-Head byte commitment is inconsistent")
        if current_projection != stop.get("lastSuccessfulHead") or not raw_head:
            raise IntegrityError("discovery continuation Head does not match")
        if not any(e.get("kind") == "refusal" and e.get("receiptSHA256") == archived["sha256"] for e in events if isinstance(e, dict)):
            raise IntegrityError("discovery event history omits the exact stop receipt")
        self.events = list(events)
        self.had_refusal = True
        self.next_q = max(1, q // 2)
        self.state["continuedFrom"] = str(self.cfg.continue_from)

    def _load_or_create(self) -> None:
        if self.state_path.exists():
            state = read_json(self.state_path)
            if state.get("schema") != STATE_SCHEMA or state.get("identity") != self.cfg.identity:
                raise ControllerError("existing controller state belongs to different inputs/build/world")
            if state.get("mode") != self.cfg.mode or state.get("action") != self.cfg.action:
                raise ControllerError("existing controller state mode/action differs")
            if state.get("status") not in ("running", "interrupted", "bounded-running-window-not-terminal"):
                raise ControllerError("completed controller result is immutable; choose a new results path")
            self.state = state
            self.events = state.get("events", [])
            if not isinstance(self.events, list):
                raise IntegrityError("state events are malformed")
            self.pending = state.get("pending")
            self.next_q = _integer(state.get("nextQuantum"), "state.nextQuantum")
            self.had_refusal = bool(state.get("hadRefusal"))
            self.state["status"] = "running"
            self._save()
        else:
            if self.cfg.results.exists() and any(self.cfg.results.iterdir()):
                raise ControllerError("results path is nonempty but lacks this controller's state; refusing overwrite")
            self.cfg.results.mkdir(parents=True, exist_ok=True)
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            self._new_state()

    def _run_child(self, label: str, command: list[str], timeout: float | None = None) -> tuple[int, bool]:
        remain = self._remaining()
        bound = remain if timeout is None else min(remain, timeout)
        log = self.logs_dir / f"{label}.log"
        with log.open("wb") as out:
            proc = subprocess.Popen(command, stdout=out, stderr=subprocess.STDOUT,
                                    cwd=str(self.cfg.world.parent.parent), env=self._env())
            try:
                code = proc.wait(timeout=bound)
                out.flush()
                os.fsync(out.fileno())
                return code, False
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                out.flush()
                os.fsync(out.fileno())
                return proc.returncode if proc.returncode is not None else -signal.SIGKILL, True
            except KeyboardInterrupt:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                out.flush()
                os.fsync(out.fileno())
                raise

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.update({"MC_ENTRY_BINDINGS": ",".join(self.cfg.names),
                    "MC_ENTRY_SELECTED_RESOURCE": self.cfg.selected,
                    "GOPROXY": "off", "GOSUMDB": "off", "PYTHONDONTWRITEBYTECODE": "1"})
        return env

    def _base_args(self) -> list[str]:
        return [str(self.cfg.world), str(self.cfg.coordinator), str(self.cfg.engine), str(self.cfg.fixture)]

    def _head(self) -> tuple[bytes, dict[str, Any]]:
        raw = _safe_head_bytes(self.cfg.world)
        head = _head_from(raw)
        _head_projection(head, self.cfg.pins, self.cfg.package_hash)
        if _integer(head.get("quantum"), "Head.quantum") < self.cfg.max_quantum:
            raise ControllerError("requested max quantum exceeds the authenticated Head's stored quantum")
        return raw, head

    def _archive_preexisting(self, receipt_path: Path, label: str) -> tuple[Path, str] | None:
        return _remove_or_archive(receipt_path, self.archive_dir, label)

    def _record_start(self) -> bool:
        """Initialize a fresh world; return False for a start refusal (no prior CP)."""
        if self.cfg.world.exists():
            raise ControllerError("--action start requires a nonexistent explicit world path")
        q = self.cfg.initial_quantum
        cmd = [str(self.cfg.driver), "setup-chain", *self._base_args(), str(q)]
        self.pending = {"kind": "start", "q": q, "phase": "running"}
        self._save()
        code, timed_out = self._run_child("start", cmd)
        if timed_out:
            self.pending = {"kind": "start", "q": q, "phase": "interrupted"}
            self._save("interrupted", "start process exceeded the explicit wall bound")
            return False
        if code != 0:
            self.pending = None
            self._save("driver-failure", f"setup-chain exit={code}")
            return False
        self.pending = None
        receipt_path = _report_dir(self.cfg.world) / "start-refusal.json"
        if receipt_path.exists():
            hraw = _safe_head_bytes(self.cfg.world)
            h = read_json(self.cfg.world / "durable-head.json", 32768)
            if not isinstance(h, dict):
                raise IntegrityError("start refusal Head is malformed")
            archived = self._archive_preexisting(receipt_path, "start-refusal")
            self.events.append({"kind": "start-refusal", "q": q,
                                "receiptSHA256": archived[1] if archived else "",
                                "epoch": h.get("epoch"), "root": h.get("trieRoot"),
                                "detail": "no successful checkpoint; never a discovery stop"})
            self._save("initial-start-refusal", "no authenticated successful checkpoint exists")
            return False
        raw, head = self._head()
        if _integer(head.get("epoch"), "Head.epoch") < 1:
            raise IntegrityError("setup-chain returned without a successful first checkpoint")
        if head.get("lifecycle") not in (1, 2, 3):
            raise IntegrityError("setup-chain returned unknown lifecycle")
        report_path = _report_dir(self.cfg.world) / "start.json"
        report = read_json(report_path)
        cp = self.cfg.world / "checkpoints" / f"{head['checkpointSHA256']}.bin"
        cp_size = _integer(report.get("checkpointBytes"), "start.checkpointBytes")
        if cp_size <= 0 or cp_size > self.cfg.pins["maxCheckpointBytes"] or cp.stat().st_size != cp_size:
            raise IntegrityError("start checkpoint byte count violates the P34 cap")
        if sha256_file(cp, self.cfg.pins["maxCheckpointBytes"]) != head["checkpointSHA256"]:
            raise IntegrityError("start checkpoint SHA256 differs from durable Head")
        event = {"kind": "start", "q": q, "epoch": head["epoch"],
                 "checkpointSHA256": head["checkpointSHA256"], "checkpointBytes": cp_size,
                 "head": canonical_head(head), "authenticatedBy": "pinned-public-Go-EVM-transport"}
        self.events.append(event)
        self._save()
        return True

    def _initialize_continuation(self) -> bool:
        raw, head = self._head()
        if _integer(head.get("epoch"), "Head.epoch") < 1:
            raise ControllerError("continuation requires a prior successful checkpoint")
        if head.get("lifecycle") in TERMINAL_LIFECYCLES:
            self._finish("terminal-outcome-not-discovery-stop", head)
            return False
        if head.get("lifecycle") != 1:
            raise IntegrityError("continuation Head is not RUNNING or a recognized terminal outcome")
        if self.cfg.continue_from:
            # _seed_from_discovery already authenticated this exact same-package Head.
            self.next_q = self.state.get("nextQuantum", self.next_q)
        else:
            # One explicit public verify is needed only for an externally supplied
            # initial Head. It is not performed per slice and is paired with the
            # corresponding final verify in this continuation-only workflow.
            if not self.events:
                self._verify_once("initial-authentication")
                raw, head = self._head()
                self.events.append({"kind": "resume-origin", "head": canonical_head(head),
                                    "authenticatedBy": "pinned-public-Go-EVM-transport-verify"})
                self._save()
            if self.next_q > _integer(head.get("quantum"), "Head.quantum"):
                self.next_q = _integer(head.get("quantum"), "Head.quantum")
        return True

    def _verify_once(self, label: str) -> None:
        q = max(1, min(self.next_q, self.cfg.max_quantum))
        cmd = [str(self.cfg.driver), "verify", *self._base_args(), str(q)]
        code, timed_out = self._run_child(label, cmd)
        if timed_out or code != 0:
            raise ControllerError(f"public EVM verification failed (exit={code}, timeout={timed_out})")
        raw, head = self._head()
        report = read_json(_report_dir(self.cfg.world) / "world-report.json")
        manifest = report.get("manifest")
        if not isinstance(manifest, dict):
            raise IntegrityError("public verifier omitted its reopened manifest")
        manifest_projection = canonical_head(manifest)
        head_projection = canonical_head(head)
        # writeManifest publishes counters before the final successful directory
        # sync and increments that actual-I/O counter only in memory afterward;
        # therefore the diagnostic world-report can be one DirectorySync ahead
        # of the durable Head. Compare all authority/guest fields, not that
        # post-publication observer-only counter snapshot.
        if {k: v for k, v in manifest_projection.items() if k != "counters"} != {k: v for k, v in head_projection.items() if k != "counters"}:
            raise IntegrityError("public verifier's reopened EVM Head differs from durable Head")
        if report.get("engineHeadOwner", "").lower() != str(head.get("coordinator", "")).lower() or report.get("engineHeadEpoch") != head.get("epoch") or report.get("engineHeadLifecycle") != head.get("lifecycle"):
            raise IntegrityError("public verifier's on-EVM Head differs from durable Head")

    def _resume_command(self, q: int) -> list[str]:
        return [str(self.cfg.driver), "resume-one-qn", *self._base_args(), str(q)]

    def _resume_once(self, q: int) -> tuple[str, dict[str, Any] | None]:
        receipt_path = _report_dir(self.cfg.world) / "resume-refusal.json"
        pending_before = _safe_head_bytes(self.cfg.world)
        before = _head_from(pending_before)
        _head_projection(before, self.cfg.pins, self.cfg.package_hash)
        if not any(e.get("kind") in ("start", "success", "resume-origin") for e in self.events if isinstance(e, dict)):
            raise IntegrityError("resume has no previously successful authenticated Head")
        if before.get("lifecycle") != 1:
            raise ControllerError("refusing to resume a non-RUNNING Head")
        # The successful call which published this Head (or the explicit initial
        # public verifier) is the authentication basis. Verify the local blob again.
        cp = self.cfg.world / "checkpoints" / f"{before['checkpointSHA256']}.bin"
        if sha256_file(cp, self.cfg.pins["maxCheckpointBytes"]) != before["checkpointSHA256"]:
            raise IntegrityError("prior successful opaque checkpoint hash mismatch")
        call_no = 1 + sum(1 for e in self.events if e.get("kind") in ("success", "refusal"))
        self._archive_preexisting(receipt_path, f"preexisting-before-call-{call_no:04d}-q{q}")
        pending = {"kind": "resume", "q": q, "phase": "running",
                   "beforeHeadBytesHex": pending_before.hex(), "beforeHeadSHA256": sha256(pending_before),
                   "beforeHead": canonical_head(before), "call": call_no}
        self.pending = pending
        self._save()
        code, timed_out = self._run_child(f"resume-{pending['call']:04d}-q{q}", self._resume_command(q))
        after_bytes = _safe_head_bytes(self.cfg.world)
        if timed_out:
            self.pending["phase"] = "interrupted"
            self._save("interrupted", "resume process exceeded the explicit wall bound; no discovery classification")
            return "interrupted", None
        self.pending["phase"] = "child-exited"
        self.pending["exitCode"] = code
        self._save()
        if code != 0:
            self._save("driver-failure", f"resume driver exit={code}; no diagnostic accepted")
            return "driver-failure", None
        if after_bytes != pending_before:
            report = read_json(_report_dir(self.cfg.world) / f"slice-{_integer(_head_from(after_bytes).get('epoch'), 'Head.epoch'):020d}.json")
            event = validate_success(before, after_bytes, self.cfg.world, self.cfg.pins, self.cfg.package_hash,
                                    q, report, self.cfg.max_call_gas)
            self.pending = None
            self.events.append({"kind": "success", **event, "authenticatedBy": "pinned-public-Go-EVM-transport"})
            self.pending = None
            self._save()
            return "success", _head_from(after_bytes)
        if not receipt_path.exists():
            self.pending = None
            self._save("driver-failure", "successful child exit changed neither Head nor wrote refusal receipt")
            return "driver-failure", None
        return self._accept_refusal(pending, pending_before, before, receipt_path)

    def _finish(self, status: str, head: dict[str, Any], detail: str | None = None, verify: bool = False) -> None:
        if verify:
            self._verify_once("final-reopen")
            _, head = self._head()
        self.state["terminalGuestOutcome"] = head.get("lifecycle") in TERMINAL_LIFECYCLES
        self.state["q1FrontierAcceptance"] = False
        self.state["finalAcceptanceEligible"] = False
        self.state["finalHead"] = canonical_head(head)
        self._save(status, detail)

    def _accept_refusal(self, pending: dict[str, Any], head_bytes: bytes, before: dict[str, Any], receipt_path: Path) -> tuple[str, dict[str, Any]]:
        receipt = read_json(receipt_path, 1024 * 1024)
        validate_atomic_refusal(receipt, head_bytes, before, self.cfg.max_call_gas)
        if _safe_head_bytes(self.cfg.world) != head_bytes:
            raise IntegrityError("failed EVM call changed durable Head bytes")
        q = pending["q"]
        archived = self._archive_preexisting(receipt_path, f"resume-{pending['call']:04d}-q{q}")
        if archived is None:
            raise IntegrityError("refusal disappeared before durable archival")
        missing = classify_missing_refusal(receipt, head_bytes, before, self.cfg.max_call_gas)
        event = {"kind": "refusal", "q": q, "selector": receipt.get("selector"),
                 "name": receipt.get("diagnostic", {}).get("name") if isinstance(receipt.get("diagnostic"), dict) else None,
                 "missingClass": missing, "receiptSHA256": archived[1],
                 "receiptArchive": str(archived[0].relative_to(self.cfg.results)),
                 "rootBefore": receipt["rootBefore"], "rootAfter": receipt["rootAfter"],
                 "priorHead": canonical_head(before), "priorHeadBytesSHA256": sha256(head_bytes),
                 "gas": receipt.get("gas"), "checkpointBytes": 0}
        self.events.append(event)
        self.pending = None
        self.had_refusal = True
        self._save()
        if self.cfg.mode == "discovery" and missing is not None and q > 1:
            self.next_q = max(1, q // 2)
            self.state["discoveryStop"] = {
                "missingClass": missing, "q": q, "nextQuantum": self.next_q,
                "priorHead": before, "priorHeadBytesHex": head_bytes.hex(),
                "priorHeadSHA256": sha256(head_bytes), "lastSuccessfulHead": canonical_head(before),
                "receiptArchive": {"path": str(archived[0].relative_to(self.cfg.results)), "sha256": archived[1]},
            }
            self._finish("discovery-missing-class-not-terminal-success-not-q1-acceptance", before)
            return "discovery-stop", before
        if q == 1:
            status = "precise-q1-refusal-not-terminal-success" if self.cfg.mode == "precise" else "q1-refusal-not-discovery-stop"
            self._finish(status, before)
            return "q1-refusal", before
        self.next_q = max(1, q // 2)
        return "refusal", before

    def _recover_pending(self) -> bool:
        if not self.pending or self.pending.get("kind") != "resume":
            return True
        pending = self.pending
        before_raw = bytes.fromhex(pending["beforeHeadBytesHex"])
        before = _head_from(before_raw)
        current_raw = _safe_head_bytes(self.cfg.world)
        receipt_path = _report_dir(self.cfg.world) / "resume-refusal.json"
        if current_raw == before_raw:
            if pending.get("phase") == "child-exited" and pending.get("exitCode") == 0:
                if not receipt_path.exists():
                    raise IntegrityError("normally exited child has neither a new Head nor a refusal receipt")
                result, _ = self._accept_refusal(pending, before_raw, before, receipt_path)
                if result in ("discovery-stop", "q1-refusal"):
                    return False
                return True
            # If this controller process died before recording normal child exit,
            # any report is ambiguous with a watchdog interruption. Archive it and
            # replay the same q from the unchanged successful Head; never classify
            # it as discovery on reopen.
            self._archive_preexisting(receipt_path, f"orphan-interrupted-{pending['call']:04d}-q{pending['q']}")
            self.pending = None
            self._save()
            return True
        # A durable one-epoch child Head can only be created by a successful
        # public Resume path; recover it as success after validation.
        epoch = _integer(_head_from(current_raw).get("epoch"), "Head.epoch")
        report = read_json(_report_dir(self.cfg.world) / f"slice-{epoch:020d}.json")
        event = validate_success(before, current_raw, self.cfg.world, self.cfg.pins, self.cfg.package_hash,
                                pending["q"], report, self.cfg.max_call_gas)
        self.events.append({"kind": "success", **event, "recoveredAfterInterruption": True,
                            "authenticatedBy": "pinned-public-Go-EVM-transport"})
        self.pending = None
        self._save()
        return True

    def _run_loop(self) -> None:
        if not self._recover_pending():
            return
        while len([e for e in self.events if e.get("kind") in ("success", "refusal")]) < self.cfg.max_calls:
            try:
                self._remaining()
            except TimeoutError:
                _, head = self._head()
                self._finish("bounded-running-window-not-terminal", head, "controller wall limit reached")
                return
            raw, head = self._head()
            life = _integer(head.get("lifecycle"), "Head.lifecycle")
            if life in TERMINAL_LIFECYCLES:
                self._finish("terminal-outcome-not-discovery-stop", head, verify=True)
                return
            if life != 1:
                raise IntegrityError("Head lifecycle is not RUNNING or terminal")
            q = self.next_q
            if q > _integer(head.get("quantum"), "Head.quantum"):
                raise ControllerError("next quantum exceeds the durable Head's stored ceiling")
            result, after = self._resume_once(q)
            if result == "success":
                assert after is not None
                if _integer(after.get("lifecycle"), "Head.lifecycle") in TERMINAL_LIFECYCLES:
                    self._finish("terminal-outcome-not-discovery-stop", after, verify=True)
                    return
                if not self.had_refusal:
                    self.next_q = min(self.cfg.max_quantum, q * 2)
                    self._save()
                continue
            if result == "discovery-stop" or result == "q1-refusal":
                # A q1 refusal is the precise stop, not a discovery early stop.
                if result == "q1-refusal":
                    self._finish(self.state["status"], after or head, verify=True)
                return
            if result == "interrupted" or result == "driver-failure":
                return
            # Any noncanonical error/OOG/watchdog-shaped refusal follows the same
            # precise halving schedule; only exact authenticated MissingClass at
            # q>1 is an early discovery stop.
            self.next_q = max(1, q // 2)
            self._save()
        _, head = self._head()
        self._finish("bounded-running-window-not-terminal", head, "max-calls reached", verify=self.cfg.mode == "precise")

    def run(self) -> dict[str, Any]:
        self.cfg.world.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_file.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            self._load_or_create()
            try:
                if self.cfg.action == "start" and not self.events:
                    if not self._record_start():
                        return self.state
                elif self.cfg.action == "continue" and not self.events:
                    if not self._initialize_continuation():
                        return self.state
                # On a fresh start, startMain's public successful receipt authenticates
                # its first Head. On continue-from, the discovery's exact EVM projection
                # and immutable refusal archive authenticate it. No per-slice view calls.
                self._run_loop()
            except KeyboardInterrupt:
                if self.pending:
                    self.pending["phase"] = "interrupted"
                self._save("interrupted", "controller interrupted; resume only from last durable successful Head")
                return self.state
            except TimeoutError as exc:
                if self.pending:
                    self.pending["phase"] = "interrupted"
                self._save("interrupted", str(exc))
                return self.state
            except Exception as exc:
                self._save("integrity-failure", f"{type(exc).__name__}: {exc}")
                raise
            return self.state


def _arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=("precise", "discovery"), default="precise",
                   help="precise is the default; discovery is an explicit non-acceptance diagnostic")
    p.add_argument("--action", choices=("start", "continue"), required=True)
    p.add_argument("--driver", type=Path, required=True)
    p.add_argument("--build", type=Path, required=True, help="explicit directory with pins.json and pinned artifacts")
    p.add_argument("--fixture-zip", type=Path, required=True)
    p.add_argument("--bindings", type=Path, required=True, help="explicit JSON {schema:1,bindings:[...],selectedResource?:...}")
    p.add_argument("--package-hash", required=True, help="explicit expected packageRoot, 0x + 32 bytes")
    p.add_argument("--engine-runtime-sha256", required=True)
    p.add_argument("--engine-runtime-keccak256", required=True)
    p.add_argument("--coordinator-runtime-sha256", required=True)
    p.add_argument("--coordinator-runtime-keccak256", required=True)
    p.add_argument("--max-call-gas", type=int, required=True)
    p.add_argument("--wall-limit-seconds", type=float, required=True)
    p.add_argument("--world", type=Path, required=True, help="explicit public transport session directory")
    p.add_argument("--results", type=Path, required=True, help="new/continued controller evidence directory")
    p.add_argument("--initial-quantum", type=int)
    p.add_argument("--max-quantum", type=int)
    p.add_argument("--max-calls", type=int, default=600)
    p.add_argument("--continue-from", type=Path,
                   help="required for precise continuation from a discovery summary; never a failed checkpoint")
    return p


def make_config(args: argparse.Namespace) -> Config:
    for key in ("driver", "build", "fixture_zip", "bindings", "world", "results"):
        p = getattr(args, key).resolve()
        setattr(args, key, p)
    if not args.driver.is_file() or not os.access(args.driver, os.X_OK):
        raise ControllerError("explicit --driver is not an executable regular file")
    if not args.fixture_zip.is_file() or args.fixture_zip.is_symlink():
        raise ControllerError("explicit --fixture-zip is not a regular file")
    if (args.world == args.results or args.world.is_relative_to(args.results) or args.results.is_relative_to(args.world)):
        raise ControllerError("world and controller results paths must be disjoint")
    package_hash = _hex32(args.package_hash, "--package-hash")
    if args.max_calls <= 0:
        raise ControllerError("--max-calls must be positive")
    if args.mode == "discovery" and args.continue_from is not None:
        raise ControllerError("a discovery run cannot continue another discovery result")
    if args.continue_from is not None and (args.action != "continue" or args.mode != "precise"):
        raise ControllerError("--continue-from is only allowed for precise --action continue")
    pins, coordinator, engine = validate_build(args.build, args)
    names, selected, binding_raw = load_bindings(args.bindings)
    identity = {
        "world": str(args.world), "fixtureSHA256": sha256_file(args.fixture_zip),
        "bindingsSHA256": sha256(binding_raw), "bindings": names, "selectedResource": selected,
        "packageHash": package_hash, "engineRuntimeSHA256": pins["engine"]["runtimeSHA256"],
        "engineRuntimeKeccak256": pins["engine"]["runtimeKeccak256"],
        "coordinatorRuntimeSHA256": pins["coordinator"]["runtimeSHA256"],
        "coordinatorRuntimeKeccak256": pins["coordinator"]["runtimeKeccak256"],
        "maxCallGas": args.max_call_gas, "maxQuantum": args.max_quantum,
        "initialQuantum": args.initial_quantum, "driverSHA256": sha256_file(args.driver),
        "coordinatorArtifactSHA256": sha256_file(coordinator), "engineArtifactSHA256": sha256_file(engine),
    }
    return Config(args.mode, args.action, args.driver, args.build, coordinator, engine,
                  args.fixture_zip, args.bindings, names, selected, binding_raw, package_hash,
                  args.world, args.results, pins, args.max_call_gas, args.wall_limit_seconds,
                  args.max_quantum, args.initial_quantum, args.max_calls,
                  args.continue_from.resolve() if args.continue_from else None, identity)


def main(argv: list[str] | None = None) -> int:
    try:
        args = _arg_parser().parse_args(argv)
        cfg = make_config(args)
        runner = Runner(cfg)
        result = runner.run()
        print(json.dumps({"status": result.get("status"), "mode": cfg.mode,
                          "terminalGuestOutcome": result.get("terminalGuestOutcome", False),
                          "q1FrontierAcceptance": result.get("q1FrontierAcceptance", False),
                          "events": len(result.get("events", [])), "summary": str(cfg.results / "summary.json")}, sort_keys=True))
        return 0 if result.get("status") not in ("integrity-failure", "driver-failure", "interrupted", "initial-start-refusal") else 2
    except ControllerError as exc:
        print(f"replay-controller: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"replay-controller: unexpected {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
