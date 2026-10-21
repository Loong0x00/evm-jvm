#!/usr/bin/env python3
"""Fast fail-closed controller tests; the separate generated-EVM gate is primary."""
import importlib.util
import json
import tempfile
import unittest
import sys
from pathlib import Path

MODULE = Path(__file__).with_name("replay_controller.py")
spec = importlib.util.spec_from_file_location("perf_replay_controller", MODULE)
controller = importlib.util.module_from_spec(spec)
assert spec.loader
sys.modules[spec.name] = controller
spec.loader.exec_module(controller)


def fake_head():
    return {
        "trieRoot": "0x" + "11" * 32,
        "engineCodeHash": "0x" + "22" * 32,
        "coordinatorCodeHash": "0x" + "33" * 32,
        "packageRoot": "0x" + "44" * 32,
        "instanceId": "0x" + "55" * 32,
        "checkpointRoot": "0x" + "66" * 32,
        "machineRoot": "0x" + "77" * 32,
        "vfsRoot": "0x" + "88" * 32,
        "engine": "0x" + "99" * 20,
        "coordinator": "0x" + "aa" * 20,
        "engineNonce": 0, "epoch": 7, "lifecycle": 1, "outcome": 1,
        "result": 0, "javaKind": 0, "javaRef": 0, "jvmSteps": 123,
        "internalSteps": 4, "quantum": 64, "slices": 7, "totalClassBytes": 42,
        "checkpointSHA256": "bb" * 32, "javaClass": None,
        "counters": {"evmCalls": 12, "gas": 100, "maxCallMs": 22, "commitMs": 7},
    }


def receipt_for(head, head_bytes, name=b"fixture/Missing"):
    raw = controller.encode_missing_class(36, 2, name)
    return {
        "selector": "0x555db429", "revertHex": "0x" + raw.hex(),
        "diagnostic": {"site": "36", "context": "2", "name": name.decode()},
        "rootBefore": head["trieRoot"], "rootAfter": head["trieRoot"],
        "rootUnchanged": True, "durableHeadUnchanged": True,
        "durableHeadSHA256Before": controller.sha256(head_bytes),
        "durableHeadSHA256After": controller.sha256(head_bytes),
        "durableHeadEpochBefore": head["epoch"], "durableHeadEpochAfter": head["epoch"],
        "checkpointBytes": 0, "candidateHead": "", "candidateCheckpoint": "",
        "candidateRoot": "", "suppliedGas": 1_000_000_000,
    }


def head_bytes(head):
    return (json.dumps(head, sort_keys=True, separators=(",", ":")) + "\n").encode()


class CanonicalABITests(unittest.TestCase):
    def test_exact_canonical_missing_error(self):
        for name in (b"java/lang/Boolean", b"fixture/RawClass"):
            raw = controller.encode_missing_class(9, 3, name)
            self.assertEqual(controller.decode_canonical_missing_class(raw), (9, 3, name))

    def test_noncanonical_offsets_trailing_bytes_and_padding_refuse(self):
        good = controller.encode_missing_class(9, 3, b"fixture/Missing")
        bad_offset = bytearray(good)
        bad_offset[4 + 64:4 + 96] = controller._word(128)
        bad_trailing = good + bytes(32)
        bad_padding = bytearray(good)
        bad_padding[-1] = 1
        for raw in (bytes(bad_offset), bad_trailing, bytes(bad_padding), b"\x00\x00"):
            self.assertIsNone(controller.decode_canonical_missing_class(raw))

    def test_selector_not_diagnostic_text_is_authority(self):
        head = fake_head()
        raw_head = head_bytes(head)
        receipt = receipt_for(head, raw_head, b"fixture/RawClass")
        self.assertEqual(controller.classify_missing_refusal(receipt, raw_head, head, 1_000_000_000), "fixture/RawClass")
        receipt["diagnostic"]["name"] = "java/lang/PlatformGuess"
        self.assertIsNone(controller.classify_missing_refusal(receipt, raw_head, head, 1_000_000_000))
        receipt["revertHex"] = "0x" + (b"\xde\xad\xbe\xef" + b"fixture/RawClass").hex()
        receipt["selector"] = "0xdeadbeef"
        self.assertIsNone(controller.classify_missing_refusal(receipt, raw_head, head, 1_000_000_000))

    def test_head_root_and_checkpoint_contradictions_fail_closed(self):
        head = fake_head()
        raw_head = head_bytes(head)
        for mutate in (
            lambda r: r.update(rootAfter="0x" + "ff" * 32),
            lambda r: r.update(durableHeadSHA256After="00" * 32),
            lambda r: r.update(durableHeadUnchanged=False),
            lambda r: r.update(checkpointBytes=1),
            lambda r: r.update(candidateCheckpoint="0x00"),
        ):
            receipt = receipt_for(head, raw_head)
            mutate(receipt)
            with self.assertRaises(controller.IntegrityError):
                controller.classify_missing_refusal(receipt, raw_head, head, 1_000_000_000)

    def test_wrong_gas_or_epoch_cannot_be_discovery(self):
        head = fake_head()
        raw_head = head_bytes(head)
        receipt = receipt_for(head, raw_head)
        receipt["suppliedGas"] += 1
        with self.assertRaises(controller.IntegrityError):
            controller.classify_missing_refusal(receipt, raw_head, head, 1_000_000_000)
        receipt = receipt_for(head, raw_head)
        receipt["durableHeadEpochBefore"] += 1
        with self.assertRaises(controller.IntegrityError):
            controller.classify_missing_refusal(receipt, raw_head, head, 1_000_000_000)


class ParserSurfaceTests(unittest.TestCase):
    def test_precise_is_default_and_scope_inputs_are_required(self):
        parser = controller._arg_parser()
        actions = {a.dest: a for a in parser._actions}
        self.assertEqual(actions["mode"].default, "precise")
        for key in ("action", "driver", "build", "fixture_zip", "bindings", "package_hash",
                    "engine_runtime_sha256", "engine_runtime_keccak256", "coordinator_runtime_sha256",
                    "coordinator_runtime_keccak256", "max_call_gas", "wall_limit_seconds", "world", "results"):
            self.assertTrue(actions[key].required, key)


class ArchiveAndRecoveryTests(unittest.TestCase):
    def test_existing_refusal_archived_without_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "resume-refusal.json"
            archive = root / "archive"
            original = b'{"old":"witness"}\n'
            src.write_bytes(original)
            saved = controller._remove_or_archive(src, archive, "preexisting")
            self.assertIsNotNone(saved)
            path, digest = saved
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(digest, controller.sha256(original))
            self.assertFalse(src.exists())
            src.write_bytes(original)
            saved2 = controller._remove_or_archive(src, archive, "preexisting")
            self.assertNotEqual(saved2[0], path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(saved2[0].read_bytes(), original)

    def test_reopen_of_unrecorded_or_timed_out_call_never_accepts_stale_diagnostic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            world = root / "world"
            reports = root / "reports" / "world"
            results = root / "results"
            world.mkdir()
            reports.mkdir(parents=True)
            results.mkdir()
            head = fake_head()
            raw_head = head_bytes(head)
            (world / "durable-head.json").write_bytes(raw_head)
            (reports / "resume-refusal.json").write_text(json.dumps(receipt_for(head, raw_head)))
            pins = {"engine": {"runtimeKeccak256": "22" * 32},
                    "coordinator": {"runtimeKeccak256": "33" * 32}, "address": head["engine"],
                    "maxCheckpointBytes": 2_097_152}
            cfg = controller.Config(
                mode="discovery", action="continue", driver=root / "driver", build=root,
                coordinator=root / "coord.json", engine=root / "engine.json", fixture=root / "fixture.zip",
                bindings_path=root / "bindings.json", names=["fixture/Main.class"], selected="", bindings_raw=b"{}",
                package_hash=head["packageRoot"], world=world, results=results, pins=pins,
                max_call_gas=1_000_000_000, wall_limit_seconds=100, max_quantum=64, initial_quantum=64,
                max_calls=10, continue_from=None, identity={"test": True})
            runner = controller.Runner(cfg)
            runner.state = {"schema": 1, "identity": cfg.identity, "mode": "discovery",
                            "action": "continue", "status": "running"}
            runner.pending = {"kind": "resume", "q": 64, "phase": "running",
                              "beforeHeadBytesHex": raw_head.hex(), "beforeHeadSHA256": controller.sha256(raw_head),
                              "beforeHead": controller.canonical_head(head), "call": 1}
            self.assertTrue(runner._recover_pending())
            self.assertEqual(runner.events, [])
            self.assertIsNone(runner.pending)
            self.assertEqual((world / "durable-head.json").read_bytes(), raw_head)
            self.assertFalse((reports / "resume-refusal.json").exists())
            archived = list((results / "refusals").glob("orphan-interrupted-*.json"))
            self.assertEqual(len(archived), 1)
            # A fresh normal child exit may consume the same canonical diagnostic;
            # this is not the ambiguous timeout/reopen case above.
            report = receipt_for(head, raw_head)
            (reports / "resume-refusal.json").write_text(json.dumps(report))
            runner.pending = {"kind": "resume", "q": 64, "phase": "child-exited", "exitCode": 0,
                              "beforeHeadBytesHex": raw_head.hex(), "beforeHeadSHA256": controller.sha256(raw_head),
                              "beforeHead": controller.canonical_head(head), "call": 1}
            self.assertFalse(runner._recover_pending())
            self.assertEqual(runner.state["status"], "discovery-missing-class-not-terminal-success-not-q1-acceptance")
            self.assertEqual(len([e for e in runner.events if e.get("kind") == "refusal"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
