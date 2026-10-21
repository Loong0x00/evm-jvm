#!/usr/bin/env python3
"""Build/check generated Java 8 fixtures and exercise the EVM diagnostic only.

The host classfile parser below is intentionally restricted to the deterministic
fixtures generated from this directory's sources; no external class/JAR input is
accepted by this script.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = ROOT / "evidence/java-evm/minecraft-entry/performance-base-p34"
GENERATED = HERE / "fixtures/generated"
RESULTS = HERE / "results"
BINDINGS = [
    "scan/Base.class",
    "scan/Bad.class",
    "scan/Helper.class",
    "scan/Marker.class",
    "scan/Probe.class",
    "scan/WrongName.class",
]
REF_OPS = {
    "new": (1, {7}), "anewarray": (1, {7}), "checkcast": (1, {7}),
    "instanceof": (1, {7}), "multianewarray": (1, {7}),
    "getstatic": (2, {9}), "putstatic": (2, {9}),
    "getfield": (2, {9}), "putfield": (2, {9}),
    "invokevirtual": (3, {10}), "invokespecial": (3, {10, 11}),
    "invokestatic": (3, {10, 11}), "invokeinterface": (3, {11}),
    "invokedynamic": (4, {18}), "ldc": (5, {7}), "ldc_w": (5, {7}),
}


def run(command: list[str], *, cwd: Path = ROOT, timeout: int = 1200) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=timeout)


def verify_p34_manifest() -> None:
    manifest = json.loads((BASE / "SOURCE_MANIFEST.json").read_text())
    assert manifest["sourceOnly"] is True
    assert manifest["noOriginalJarClassesResourcesWorldsCheckpointsReceiptsOrBindingLists"] is True
    for item in manifest["files"]:
        data = (BASE / item["path"]).read_bytes()
        assert len(data) == item["bytes"], item["path"]
        assert hashlib.sha256(data).hexdigest() == item["sha256"], item["path"]


def u1(data: bytes, at: int) -> int:
    if at < 0 or at >= len(data):
        raise ValueError(f"truncated u1 at {at}")
    return data[at]


def u2(data: bytes, at: int) -> int:
    if at < 0 or at + 2 > len(data):
        raise ValueError(f"truncated u2 at {at}")
    return int.from_bytes(data[at:at + 2], "big")


def u4(data: bytes, at: int) -> int:
    if at < 0 or at + 4 > len(data):
        raise ValueError(f"truncated u4 at {at}")
    return int.from_bytes(data[at:at + 4], "big")


def parse_generated_class(data: bytes) -> tuple[list[dict | None], list[dict], int]:
    """Fixture-only classfile oracle; javap is independently checked below."""
    if len(data) < 10 or data[:4] != bytes.fromhex("cafebabe"):
        raise ValueError("generated fixture class magic/length")
    cp_count = u2(data, 8)
    cp: list[dict | None] = [None] * cp_count
    at = 10
    i = 1
    while i < cp_count:
        tag = u1(data, at)
        at += 1
        if tag == 1:
            size = u2(data, at)
            at += 2
            if at + size > len(data):
                raise ValueError("truncated generated UTF8")
            cp[i] = {"tag": tag, "bytes": data[at:at + size]}
            at += size
        elif tag in (7, 8, 16, 19, 20):
            cp[i] = {"tag": tag, "a": u2(data, at)}
            at += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            cp[i] = {"tag": tag, "a": u2(data, at), "b": u2(data, at + 2)}
            at += 4
        elif tag in (3, 4):
            cp[i] = {"tag": tag}
            at += 4
        elif tag in (5, 6):
            cp[i] = {"tag": tag}
            at += 8
            i += 1
            if i < cp_count:
                cp[i] = {"tag": 0}
        elif tag == 15:
            cp[i] = {"tag": tag, "a": u1(data, at), "b": u2(data, at + 1)}
            at += 3
        else:
            raise ValueError(f"unsupported generated constant tag {tag}")
        if at > len(data):
            raise ValueError("generated constant pool truncated")
        i += 1

    def utf(index: int) -> bytes:
        entry = cp[index] if 0 < index < len(cp) else None
        if not entry or entry["tag"] != 1:
            raise ValueError(f"generated constant {index} is not UTF8")
        return entry["bytes"]

    at += 6  # access, this, super
    interfaces = u2(data, at)
    at += 2 + interfaces * 2
    fields = u2(data, at)
    at += 2

    def skip_attrs(pos: int, count: int) -> int:
        for _ in range(count):
            _ = utf(u2(data, pos))
            size = u4(data, pos + 2)
            pos += 6
            if pos + size > len(data):
                raise ValueError("generated attribute truncated")
            pos += size
        return pos

    for _ in range(fields):
        name = utf(u2(data, at + 2))
        desc = utf(u2(data, at + 4))
        _ = name, desc
        count = u2(data, at + 6)
        at = skip_attrs(at + 8, count)

    method_count = u2(data, at)
    at += 2
    methods: list[dict] = []
    for index in range(method_count):
        name = utf(u2(data, at + 2)).decode("ascii")
        desc = utf(u2(data, at + 4)).decode("ascii")
        count = u2(data, at + 6)
        at += 8
        method = {"index": index, "name": name, "descriptor": desc, "code": b"", "codeLength": 0}
        for _ in range(count):
            attr_name = utf(u2(data, at)).decode("ascii")
            length = u4(data, at + 2)
            body = at + 6
            if body + length > len(data):
                raise ValueError("generated method attribute truncated")
            if attr_name == "Code":
                code_len = u4(data, body + 4)
                code_start = body + 8
                if code_start + code_len > body + length:
                    raise ValueError("generated Code truncated")
                method["code"] = data[code_start:code_start + code_len]
                method["codeLength"] = code_len
            at = body + length
        methods.append(method)
    class_attrs = u2(data, at)
    at = skip_attrs(at + 2, class_attrs)
    if at != len(data):
        raise ValueError("generated class trailing data")
    return cp, methods, at


def cp_utf(cp: list[dict | None], index: int) -> str:
    entry = cp[index]
    if entry is None or entry["tag"] != 1:
        raise ValueError(f"fixture oracle CP#{index} not UTF8")
    return entry["bytes"].decode("ascii")


def cp_symbol(cp: list[dict | None], index: int, kind: int) -> dict:
    entry = cp[index]
    if entry is None:
        raise ValueError(f"fixture oracle missing CP#{index}")
    tag = entry["tag"]
    wanted_kind, allowed_tags = next((v for _, v in REF_OPS.items() if v[0] == kind and tag in v[1]), (kind, set()))
    if tag not in allowed_tags:
        raise ValueError(f"fixture oracle CP#{index} tag {tag} unexpected for kind {kind}")
    out = {"kind": kind, "constantPoolTag": tag, "constantPoolIndex": index,
           "owner": "", "name": "", "descriptor": "", "typeName": ""}
    if kind in (1, 5):
        klass = cp[entry["a"]]
        if klass is None or klass["tag"] != 1:
            raise ValueError("fixture oracle class constant malformed")
        out["typeName"] = cp_utf(cp, entry["a"])
    elif kind in (2, 3):
        owner = cp[entry["a"]]
        nat = cp[entry["b"]]
        if owner is None or owner["tag"] != 7 or nat is None or nat["tag"] != 12:
            raise ValueError("fixture oracle member constant malformed")
        out["owner"] = cp_utf(cp, owner["a"])
        out["name"] = cp_utf(cp, nat["a"])
        out["descriptor"] = cp_utf(cp, nat["b"])
    elif kind == 4:
        nat = cp[entry["b"]]
        if nat is None or nat["tag"] != 12:
            raise ValueError("fixture oracle invokedynamic malformed")
        out["name"] = cp_utf(cp, nat["a"])
        out["descriptor"] = cp_utf(cp, nat["b"])
    return out


def parse_javap(text: str, methods: list[dict], cp: list[dict | None]) -> dict[tuple[str, str], dict]:
    instruction_re = re.compile(r"^\s*(\d+):\s+([a-z0-9_]+)(?:\s+(.*))?$")
    descriptor_re = re.compile(r"^\s*descriptor:\s+(\S+)\s*$")
    method_by_sig = {(m["name"], m["descriptor"]): m for m in methods}
    used: set[tuple[str, str]] = set()
    out: dict[tuple[str, str], dict] = {}
    current: dict | None = None
    for line in text.splitlines():
        dm = descriptor_re.match(line)
        if dm:
            desc = dm.group(1)
            current = None
            if desc.startswith("("):
                candidates = [m for m in methods if m["descriptor"] == desc and (m["name"], desc) not in used]
                if not candidates:
                    raise ValueError(f"javap method descriptor absent in generated class: {desc}")
                current = candidates[0]
                used.add((current["name"], desc))
                out[(current["name"], desc)] = {"instructions": [], "references": []}
            continue
        if current is None:
            continue
        match = instruction_re.match(line)
        if not match:
            continue
        pc = int(match.group(1))
        opcode = match.group(2)
        if opcode.isdigit():  # switch case-key rows in javap, not instructions
            continue
        operands = match.group(3) or ""
        instruction = {"pc": pc, "opcode": opcode, "operands": operands}
        item = out[(current["name"], current["descriptor"])]
        item["instructions"].append(instruction)
        if opcode not in REF_OPS:
            continue
        cp_match = re.search(r"#(\d+)", operands)
        if not cp_match:
            raise ValueError(f"javap omitted CP index for {opcode} at {pc}: {line}")
        cp_index = int(cp_match.group(1))
        kind, allowed = REF_OPS[opcode]
        if opcode in ("ldc", "ldc_w") and cp[cp_index]["tag"] != 7:
            continue
        symbol = cp_symbol(cp, cp_index, kind)
        if symbol["constantPoolTag"] not in allowed:
            raise ValueError(f"javap CP tag mismatch at {pc} {opcode}")
        item["references"].append({"pc": pc, "opcode": opcode, **symbol})
    if len(used) != len(methods):
        missing = sorted(set(method_by_sig) - used)
        raise ValueError(f"javap did not list generated methods: {missing}")
    return out


def generated_inputs(rebuild: bool) -> tuple[Path, dict, dict]:
    existed = GENERATED.exists()
    if existed and rebuild:
        shutil.rmtree(GENERATED)
        existed = False
    classes = GENERATED / "classes"
    if not existed:
        classes.mkdir(parents=True)
    sources = sorted((HERE / "fixtures/src").rglob("*.java"))
    rebuilt_javap: str | None = None
    if existed:
        for src in sources:
            if not src.is_file():
                raise FileNotFoundError(src)
        # Recompile into an isolated disposable directory and compare bytes; this
        # prevents a stale checked-in fixture from becoming the EVM test input.
        with tempfile.TemporaryDirectory(prefix="perf-entry-generated-") as tmp:
            temp_classes = Path(tmp) / "classes"
            temp_classes.mkdir()
            run(["javac", "--release", "8", "-g:none", "-Xlint:-options", "-d", str(temp_classes), *map(str, sources)])
            for name in ("Base", "Helper", "Marker", "Probe"):
                stored = (classes / f"scan/{name}.class").read_bytes()
                rebuilt = (temp_classes / f"scan/{name}.class").read_bytes()
                if stored != rebuilt:
                    raise ValueError(f"stored generated class differs from current javac output: {name}")
            rebuilt_javap = run(["javap", "-v", "-p", "-c", "-s", "-classpath", str(temp_classes), "scan.Probe"]).stdout
    else:
        run(["javac", "--release", "8", "-g:none", "-Xlint:-options", "-d", str(classes), *map(str, sources)])
    probe = classes / "scan/Probe.class"
    raw_probe = probe.read_bytes()
    cp, methods, _ = parse_generated_class(raw_probe)
    javap_path = GENERATED / "javap-Probe.txt"
    if existed and not javap_path.is_file():
        raise FileNotFoundError(javap_path)
    if existed:
        javap_text = javap_path.read_text()
    else:
        javap = run(["javap", "-v", "-p", "-c", "-s", "-classpath", str(classes), "scan.Probe"])
        javap_text = javap.stdout
        javap_path.write_text(javap_text)
    javap_meta = parse_javap(javap_text, methods, cp)
    if rebuilt_javap is not None and parse_javap(rebuilt_javap, methods, cp) != javap_meta:
        raise ValueError("stored javap instruction oracle differs from current javac class output")
    class_content = {
        "scan/Base.class": (classes / "scan/Base.class").read_bytes(),
        "scan/Bad.class": raw_probe[:19],
        "scan/Helper.class": (classes / "scan/Helper.class").read_bytes(),
        "scan/Marker.class": (classes / "scan/Marker.class").read_bytes(),
        "scan/Probe.class": raw_probe,
        # Valid classfile bytes deliberately bound under a different coordinator name.
        "scan/WrongName.class": (classes / "scan/Helper.class").read_bytes(),
    }
    zip_path = GENERATED / "fixture.zip"
    if existed:
        if not zip_path.is_file():
            raise FileNotFoundError(zip_path)
        with zipfile.ZipFile(zip_path) as archive:
            if archive.namelist() != BINDINGS:
                raise ValueError("preserved generated fixture ZIP binding set/order changed")
            for name in BINDINGS:
                if archive.read(name) != class_content[name]:
                    raise ValueError(f"preserved generated ZIP entry differs: {name}")
    else:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as archive:
            for name in BINDINGS:
                info = zipfile.ZipInfo(name, date_time=(2024, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, class_content[name])
        # No archive enumeration drives the binding list: it remains this literal generated test set.
        (GENERATED / "method-oracle.json").write_text(json.dumps({
            "provenance": "fixture-only javac --release 8 + javap -v -p -c -s",
            "methods": [{k: v for k, v in m.items() if k != "code"} for m in methods],
        }, indent=2) + "\n")
    parsed = {"cp": cp, "methods": methods, "javap": javap_meta}
    return zip_path, parsed, class_content


def build_requests(parsed: dict) -> tuple[list[dict], list[dict], dict]:
    methods = parsed["methods"]
    javap = parsed["javap"]
    by_name: dict[str, dict] = {}
    for method in methods:
        if method["name"] in by_name:
            raise ValueError(f"fixture method name unexpectedly overloaded: {method['name']}")
        by_name[method["name"]] = method
    names = ["<init>", "<clinit>", "dependencies", "getCurrent", "setCurrent", "interfaceCall",
             "virtualCall", "staticCall", "classLiteral", "operandTrap", "fixturePadding",
             "tableSwitch", "lookupSwitch", "wideLocals"]
    success: list[dict] = []
    for name in names:
        method = by_name[name]
        code_length = method["codeLength"]
        if not code_length:
            raise ValueError(f"fixture method {name} has no Code")
        success.append({"label": f"Probe.{name}", "binding": 4, "methodIndex": method["index"],
                        "pcStart": 0, "pcEnd": code_length, "maxResults": 64, "expectSuccess": True})
    dep_method = by_name["dependencies"]
    dep_oracle = javap[(dep_method["name"], dep_method["descriptor"])]
    first_ref = dep_oracle["references"][0]
    unaligned_end = first_ref["pc"] + 1
    negatives = [
        {"label": "truncated-class", "binding": 1, "methodIndex": 0, "pcStart": 0, "pcEnd": 1, "maxResults": 8, "expectSuccess": False},
        {"label": "binding-name-mismatch", "binding": 5, "methodIndex": 0, "pcStart": 0, "pcEnd": 1, "maxResults": 8, "expectSuccess": False},
        {"label": "pc-end-inside-operand", "binding": 4, "methodIndex": dep_method["index"], "pcStart": 0, "pcEnd": unaligned_end, "maxResults": 64, "expectSuccess": False},
        {"label": "reference-cap", "binding": 4, "methodIndex": dep_method["index"], "pcStart": 0,
         "pcEnd": dep_method["codeLength"], "maxResults": 1, "expectSuccess": False},
    ]
    return success, negatives, by_name


def verify_summary(summary: dict, success: list[dict], negatives: list[dict], parsed: dict, class_content: dict) -> dict:
    assert summary["diagnosticOnly"] and not summary["guestExecution"] and not summary["checkpointOrContinuation"]
    assert not summary["worldOrPackageMutationByInspector"]
    assert summary["wrongPackageRootConstructorRefused"]
    assert summary["wrongCoordinatorCodeHashConstructorRefused"]
    guard_fields = {"coordinator-owner", "coordinator-packageRoot", "coordinator-finalIndexRoot",
                    "di0-owner", "di0-phase", "di0-indexRoot", "di0-plainSize", "di0-finalRoot"}
    assert set(summary["forgedStateGuardSlots"]) == guard_fields
    assert (summary["totalObservedEVMGas"] + summary["forgedStateGuardProbeGas"] +
            summary["otherNegativeProbeGas"]) <= 1_000_000_000
    assert summary["maximumObservedEVMCallGas"] <= 1_000_000_000
    results = {item["label"]: item for item in summary["results"]}
    for request in success:
        item = results[request["label"]]
        assert item["success"], (request["label"], item.get("error"))
        assert item["resourceName"] == BINDINGS[request["binding"]]
        assert item["bindingIndex"] == request["binding"]
        assert item["coordinator"] == summary["coordinator"]
        assert item["coordinatorCodeHash"] == summary["coordinatorCodeHash"]
        assert item["packageRoot"] == summary["packageRoot"]
        assert item["indexRoot"] == summary["indexRoot"]
        binding_size = summary["bindingSizes"][request["binding"]]
        assert sum(item["stats"].get("di0ReadSizes", [])) == binding_size
        assert all(0 < n <= 4096 for n in item["stats"].get("di0ReadSizes", []))
        assert item["codeLength"] == request["pcEnd"]
        meth = next(m for m in parsed["methods"] if m["index"] == request["methodIndex"])
        oracle = parsed["javap"][(meth["name"], meth["descriptor"])]
        assert item["decodedInstructions"] == len(oracle["instructions"]), (request["label"], item["decodedInstructions"], len(oracle["instructions"]))
        assert item.get("switchInstructions", 0) == sum(i["opcode"] in ("tableswitch", "lookupswitch") for i in oracle["instructions"])
        if meth["name"] == "wideLocals":
            assert item.get("wideInstructions", 0) > 0
        if meth["name"] in ("operandTrap", "fixturePadding"):
            assert not item.get("references"), (meth["name"], item.get("references"))
        expected = sorted((r["pc"], r["opcode"], r["constantPoolIndex"], r["constantPoolTag"], r["kind"],
                           r["owner"], r["name"], r["descriptor"], r["typeName"]) for r in oracle["references"])
        got = sorted((r["pc"], r["opcode"], r["constantPoolIndex"], r["constantPoolTag"], r["kind"],
                      r.get("owner", ""), r.get("name", ""), r.get("descriptor", ""), r.get("typeName", "")) for r in item.get("references", []))
        assert got == expected, (request["label"], got, expected)
        for reference in item.get("references", []):
            if reference["kind"] == 1:
                provenance = "Code operand -> CONSTANT_Class"
            elif reference["kind"] == 2:
                provenance = "Code operand -> CONSTANT_Fieldref"
            elif reference["kind"] == 3 and reference["constantPoolTag"] == 10:
                provenance = "Code operand -> CONSTANT_Methodref"
            elif reference["kind"] == 3:
                provenance = "Code operand -> CONSTANT_InterfaceMethodref"
            elif reference["kind"] == 4:
                provenance = "Code operand -> CONSTANT_InvokeDynamic/NameAndType"
            else:
                provenance = "ldc operand -> CONSTANT_Class"
            assert reference["provenance"] == provenance, reference
    for request in negatives:
        item = results[request["label"]]
        assert not item["success"] and item.get("error"), (request["label"], item)
    assert not results["invalid-binding"]["success"]
    assert not results["tamper-coordinator-code"]["success"]
    assert not results["tamper-di0-code"]["success"]
    # The published code hash is checked against the actual generated probe bytes via local js-sha3.
    probe_hash = run(["node", "-e", "const fs=require('fs');const {keccak256}=require('./jvmevm/runtime/node_modules/js-sha3');process.stdout.write(keccak256(fs.readFileSync(process.argv[1])))", str(GENERATED / "classes/scan/Probe.class")]).stdout
    probe_item = results["Probe.dependencies"]
    assert probe_item["classBytesKeccak"].lower().removeprefix("0x") == probe_hash.lower()
    assert len(class_content["scan/Bad.class"]) == 19
    return {"generatedProbeClassBytes": len(class_content["scan/Probe.class"]),
            "generatedZipBytes": summary["fixtureZIPBytes"],
            "positiveMethodsCrosschecked": len(success),
            "negativeControls": len(negatives) + 3 + len(guard_fields),
            "referenceRowsCrosschecked": sum(len(item.get("references", [])) for item in results.values() if item["success"]),
            "decodedInstructionsCrosschecked": sum(item["decodedInstructions"] for item in results.values() if item["success"]),
            "switchMethods": ["Probe.tableSwitch", "Probe.lookupSwitch"],
            "wideMethod": "Probe.wideLocals",
            "perCallReadLimit": 4096}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild-generated", action="store_true", help="recreate only this directory's deterministic generated Java fixtures")
    parser.add_argument("--summary", type=Path, default=RESULTS / "generated-only-summary.json")
    args = parser.parse_args()
    verify_p34_manifest()
    run(["node", str(HERE / "build.js"), "--check"])
    zip_path, parsed, class_content = generated_inputs(args.rebuild_generated)
    success, negatives, _ = build_requests(parsed)
    RESULTS.mkdir(exist_ok=True)
    config_path = RESULTS / "generated-fixture-config.json"
    config = {
        "zipPath": str(zip_path.relative_to(ROOT)),
        "coordinatorArtifact": str((BASE / "coordinator/MCEntryCoordinator.json").relative_to(ROOT)),
        "engineArtifact": str((BASE / "engine/MCEntryInterpreter.json").relative_to(ROOT)),
        "inspectorArtifact": str((HERE / "BindingMethodInspector.json").relative_to(ROOT)),
        "bindings": BINDINGS,
        "requests": success,
        "negativeRequests": negatives,
        "tamperBinding": 4,
        "invalidBinding": 250,
        "runWrongPackageConstructor": True,
        "runWrongCodeConstructor": True,
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    command = ["go", "run", "./evidence/java-evm/minecraft-entry/perf-evm-dependency-preflight/tools/generated_evm.go",
               str(config_path.relative_to(ROOT))]
    completed = run(command, timeout=1200)
    try:
        summary = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        raise RuntimeError("generated EVM helper did not return JSON") from exc
    checked = verify_summary(summary, success, negatives, parsed, class_content)
    summary["fixtureOracleChecks"] = checked
    summary["p34SourceManifestVerified"] = True
    summary["solidityBuild"] = "solc 0.8.30 pinned artifact matches source"
    summary["javac"] = "javac --release 8 -g:none"
    summary["javapOracle"] = "javap -v -p -c -s on generated Probe only"
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(summary, indent=2) + "\n"
    if args.summary.exists() and args.summary.read_text() != rendered:
        raise FileExistsError(f"refusing to replace different summary {args.summary}; choose a fresh --summary path")
    args.summary.write_text(rendered)
    print(json.dumps({"summary": str(args.summary), "fixtureOracleChecks": checked,
                      "elapsedMillis": summary["elapsedMillis"], "inspectorRuntimeBytes": summary["inspectorRuntimeBytes"]}, indent=2))


if __name__ == "__main__":
    main()
