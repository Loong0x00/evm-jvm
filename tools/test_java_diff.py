#!/usr/bin/env python3
"""Tests for tools/java_diff.py, including an opt-in real M1 EVM smoke."""

import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("java_diff", HERE / "java_diff.py")
java_diff = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(java_diff)

ORACLE_SOURCE = """
import java.lang.reflect.*;
public final class OracleMain {
  public static void main(String[] a) throws Exception {
    Class<?> c = Class.forName(a[0]);
    Class<?>[] p = new Class<?>[a.length - 2];
    Object[] v = new Object[a.length - 2];
    for (int i = 0; i < p.length; i++) { p[i] = int.class; v[i] = Integer.valueOf(a[i+2]); }
    try { System.out.println("value=" + c.getMethod(a[1], p).invoke(null, v)); }
    catch (InvocationTargetException e) {
      System.out.println("exception=" + e.getCause().getClass().getName());
    }
  }
}
"""

GUEST_SOURCE = """
public final class Arithmetic {
  public static int add(int a, int b) { return a + b; }
  public static int identity(int a) { return a; }
}
"""


def case(case_id="m1-add", stage="m1", method="add", args=None, smoke=True,
         timeout=1, expected_kind="value",
         expected_exception="java.lang.ArithmeticException"):
    fixture = {
        "id": case_id,
        "stage": stage,
        "sources": ["Arithmetic.java"],
        "class": "Arithmetic",
        "method": method,
        "args": [20, 22] if args is None else args,
        "gas_limit": 2_000_000,
        "timeout_seconds": timeout,
        "smoke": smoke,
        "expected_kind": expected_kind,
    }
    if expected_kind == "java_exception":
        fixture["expected_exception"] = expected_exception
    return fixture


class FixtureTree:
    def __init__(self, root, cases):
        self.path = Path(root) / "fixtures"
        self.path.mkdir()
        (self.path / "OracleMain.java").write_text(ORACLE_SOURCE, encoding="utf-8")
        (self.path / "Arithmetic.java").write_text(GUEST_SOURCE, encoding="utf-8")
        self.write_cases(cases)

    def write_cases(self, cases):
        (self.path / "cases.json").write_text(
            json.dumps({"schema_version": 1, "cases": cases}), encoding="utf-8"
        )


def executable(path, source):
    path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class MockTools:
    def __init__(self, root):
        self.bin = Path(root) / "mock-bin"
        self.bin.mkdir()
        executable(self.bin / "javac", r'''
            #!/usr/bin/env python3
            import pathlib, sys
            if "-version" in sys.argv:
                print("javac mock-8")
                raise SystemExit(0)
            out = pathlib.Path(sys.argv[sys.argv.index("-d") + 1])
            out.mkdir(parents=True, exist_ok=True)
            for arg in sys.argv:
                if arg.endswith(".java"):
                    (out / (pathlib.Path(arg).stem + ".class")).write_bytes(b"raw-class")
        ''')
        executable(self.bin / "java", r'''
            #!/usr/bin/env python3
            import os, sys, time
            if "-version" in sys.argv:
                print("openjdk mock-8", file=sys.stderr)
                raise SystemExit(0)
            mode = os.environ.get("MOCK_JAVA_MODE", "value")
            if mode == "timeout":
                time.sleep(2)
            if mode == "failure":
                print("oracle configuration failed", file=sys.stderr)
                raise SystemExit(3)
            if mode == "malformed":
                print("not-protocol")
                raise SystemExit(0)
            marker = sys.argv.index("OracleMain")
            method = sys.argv[marker + 2]
            if mode == "exception" or (mode == "by-method" and method == "divide"):
                print("exception=" + os.environ.get(
                    "MOCK_JAVA_EXCEPTION", "java.lang.ArithmeticException"))
                raise SystemExit(0)
            if mode == "malformed-exception":
                print("exception=not qualified")
                raise SystemExit(0)
            values = [int(x) for x in sys.argv[marker + 3:]]
            result = values[0] if method == "identity" else sum(values)
            print("value=" + str(result))
        ''')
        self.evm = self.bin / "jvmevm"
        executable(self.evm, r'''
            #!/usr/bin/env python3
            import os, sys, time
            mode = os.environ.get("MOCK_EVM_MODE", "value")
            if mode == "timeout":
                time.sleep(2)
            if mode == "oog":
                print("jvmevm: out of gas (gas_used=99 runtime_sha256=" + "a"*64 + ")", file=sys.stderr)
                raise SystemExit(1)
            if mode == "revert":
                print("jvmevm: execution reverted (gas_used=88 runtime_sha256=" + "a"*64 + ")", file=sys.stderr)
                raise SystemExit(1)
            if mode == "malformed":
                print("result=42")
                raise SystemExit(0)
            arg = next(x for x in sys.argv if x.startswith("-args="))[6:]
            values = [] if not arg else [int(x) for x in arg.split(",")]
            method = sys.argv[sys.argv.index("-method") + 1]
            result = values[0] if method == "identity" else sum(values)
            if mode == "mismatch":
                result += 1
            exception_outcome = mode in ("exception", "exception-gasbad")
            exception_outcome = exception_outcome or (
                mode in ("by-method", "exception-runtime-change") and method == "divide")
            runtime_hash = "b"*64 if (
                (mode == "runtime-change" and method == "identity")
                or (mode == "exception-runtime-change" and method == "divide")
            ) else "a"*64
            print("engine=evm-jvm-subset-interpreter")
            print("runtime_bytes=123")
            print("runtime_sha256=" + runtime_hash)
            if mode == "both":
                print("result=" + str(result))
                print("exception=java.lang.ArithmeticException")
            elif mode == "malformed-exception":
                print("exception=not-qualified")
            elif exception_outcome:
                print("exception=" + os.environ.get(
                    "MOCK_EVM_EXCEPTION", "java.lang.ArithmeticException"))
            else:
                print("result=" + str(result))
            print("gas_used=" + ("0" if mode == "exception-gasbad" else "456"))
        ''')

    def environment(self, **extra):
        env = os.environ.copy()
        env["PATH"] = str(self.bin) + os.pathsep + env.get("PATH", "")
        env.update(extra)
        return env


class JavaDiffTests(unittest.TestCase):
    def run_runner(self, root, fixtures, tools, *extra, env_extra=None):
        artifacts = Path(root) / "artifacts"
        command = [
            sys.executable, str(HERE / "java_diff.py"),
            "--fixtures", str(fixtures), "--artifacts", str(artifacts),
            "--evm-bin", str(tools.evm), *extra,
        ]
        completed = subprocess.run(
            command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=tools.environment(**(env_extra or {})), timeout=10,
        )
        report = json.loads((artifacts / "report.json").read_text(encoding="utf-8"))
        return completed, report

    def test_mock_success_stage_selection_and_report_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("m1-smoke"), case("m1-other", smoke=False),
                case("m2-smoke", stage="m2"),
            ])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools, "--stage", "m1", "--tier", "full"
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(report["selected_ids"], ["m1-smoke", "m1-other"])
            self.assertEqual(report["status_counts"], {"pass": 2})
            self.assertEqual(report["runtime_sha256"], "a" * 64)
            self.assertIn("javac mock-8", report["commands"]["javac_version"]["stdout"])
            for result in report["cases"]:
                self.assertIn("class_sha256", result)
                self.assertEqual(result["gas_used"], 456)
                self.assertIn("stdout", result["oracle"])
                self.assertIn("stdout", result["evm"])

    def test_matching_expected_java_exception_passes_with_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("m2b-div-zero", stage="m2b", method="divide", args=[7, 0],
                     expected_kind="java_exception"),
            ])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools,
                env_extra={"MOCK_JAVA_MODE": "exception", "MOCK_EVM_MODE": "exception"},
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = report["cases"][0]
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["oracle_exception"], "java.lang.ArithmeticException")
            self.assertEqual(result["evm_exception"], "java.lang.ArithmeticException")
            self.assertEqual(result["gas_used"], 456)
            self.assertEqual(report["runtime_sha256"], "a" * 64)

    def test_wrong_java_exception_class_is_a_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("wrong-exception", stage="m2b", method="divide", args=[7, 0],
                     expected_kind="java_exception"),
            ])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools,
                env_extra={
                    "MOCK_JAVA_MODE": "exception", "MOCK_EVM_MODE": "exception",
                    "MOCK_EVM_EXCEPTION": "java.lang.NullPointerException",
                },
            )
            self.assertNotEqual(completed.returncode, 0)
            result = report["cases"][0]
            self.assertEqual(result["status"], "mismatch")
            self.assertEqual(result["oracle_exception"], "java.lang.ArithmeticException")
            self.assertEqual(result["evm_exception"], "java.lang.NullPointerException")

    def test_value_exception_disagreement_fails_in_both_directions(self):
        scenarios = [
            (case("value-to-exception"), {"MOCK_EVM_MODE": "exception"}),
            (case("exception-to-value", stage="m2b", method="divide", args=[7, 0],
                  expected_kind="java_exception"), {"MOCK_JAVA_MODE": "exception"}),
        ]
        for fixture_case, environment in scenarios:
            with self.subTest(case=fixture_case["id"]), tempfile.TemporaryDirectory() as tmp:
                fixtures = FixtureTree(tmp, [fixture_case])
                tools = MockTools(tmp)
                completed, report = self.run_runner(
                    tmp, fixtures.path, tools, env_extra=environment,
                )
                self.assertNotEqual(completed.returncode, 0)
                self.assertEqual(report["cases"][0]["status"], "mismatch")

    def test_unexpected_or_wrong_oracle_exception_fails_before_evm(self):
        scenarios = [
            (case("unexpected-oracle"), {}, "unexpected oracle exception"),
            (case("wrong-oracle", stage="m2b", expected_kind="java_exception"),
             {"MOCK_JAVA_EXCEPTION": "java.lang.NullPointerException"},
             "expected oracle exception"),
        ]
        for fixture_case, extra, detail in scenarios:
            with self.subTest(case=fixture_case["id"]), tempfile.TemporaryDirectory() as tmp:
                fixtures = FixtureTree(tmp, [fixture_case])
                tools = MockTools(tmp)
                environment = {"MOCK_JAVA_MODE": "exception", **extra}
                completed, report = self.run_runner(
                    tmp, fixtures.path, tools, env_extra=environment,
                )
                self.assertNotEqual(completed.returncode, 0)
                result = report["cases"][0]
                self.assertEqual(result["status"], "oracle_exception")
                self.assertIn(detail, result["detail"])
                self.assertIn("oracle_exception", result)
                self.assertNotIn("evm", result)

    def test_exception_output_malformed_or_both_outcomes_is_rejected(self):
        for mode in ("malformed-exception", "both"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                fixtures = FixtureTree(tmp, [case()])
                tools = MockTools(tmp)
                completed, report = self.run_runner(
                    tmp, fixtures.path, tools, env_extra={"MOCK_EVM_MODE": mode},
                )
                self.assertNotEqual(completed.returncode, 0)
                self.assertEqual(report["cases"][0]["status"], "evm_malformed")

    def test_runtime_hash_identity_includes_exception_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("value-first"),
                case("exception-second", stage="m2b", method="divide", args=[7, 0],
                     expected_kind="java_exception"),
            ])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools, "--tier", "full",
                env_extra={
                    "MOCK_JAVA_MODE": "by-method",
                    "MOCK_EVM_MODE": "exception-runtime-change",
                },
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(report["cases"][0]["status"], "pass")
            self.assertEqual(report["cases"][1]["evm_status"], "java_exception")
            self.assertEqual(report["cases"][1]["status"], "harness_error")
            self.assertIn("runtime_sha256 differs", report["cases"][1]["detail"])

    def test_exception_success_requires_positive_bounded_gas(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("exception-gas", stage="m2b", expected_kind="java_exception"),
            ])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools,
                env_extra={
                    "MOCK_JAVA_MODE": "exception", "MOCK_EVM_MODE": "exception-gasbad",
                },
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(report["cases"][0]["status"], "evm_malformed")

    def test_expected_exception_never_accepts_revert_or_oog(self):
        for mode, status in (("revert", "evm_revert"), ("oog", "evm_oog")):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                fixtures = FixtureTree(tmp, [
                    case("exception-engine-failure", stage="m2b",
                         expected_kind="java_exception"),
                ])
                tools = MockTools(tmp)
                completed, report = self.run_runner(
                    tmp, fixtures.path, tools,
                    env_extra={"MOCK_JAVA_MODE": "exception", "MOCK_EVM_MODE": mode},
                )
                self.assertNotEqual(completed.returncode, 0)
                self.assertEqual(report["cases"][0]["status"], status)

    def test_repeated_runs_preserve_existing_files_and_archive_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [case()])
            tools = MockTools(tmp)
            existing = Path(tmp) / "artifacts/compiled/keep.txt"
            existing.parent.mkdir(parents=True)
            existing.write_text("not owned by the runner", encoding="utf-8")
            first, first_report = self.run_runner(tmp, fixtures.path, tools)
            second, second_report = self.run_runner(tmp, fixtures.path, tools)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(existing.read_text(encoding="utf-8"), "not owned by the runner")
            self.assertNotEqual(first_report["run_directory"], second_report["run_directory"])
            for report in (first_report, second_report):
                directory = Path(report["run_directory"])
                self.assertTrue((directory / "compiled/Arithmetic.class").is_file())
                archived = json.loads((directory / "report.json").read_text(encoding="utf-8"))
                self.assertEqual(archived["status_counts"], {"pass": 1})

    def test_success_gas_cannot_exceed_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            too_little_gas = case()
            too_little_gas["gas_limit"] = 100
            fixtures = FixtureTree(tmp, [too_little_gas])
            tools = MockTools(tmp)  # claims success with gas_used=456
            completed, report = self.run_runner(tmp, fixtures.path, tools)
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(report["cases"][0]["status"], "evm_malformed")

    def test_revert_data_alone_is_not_a_revert_classification(self):
        record = {
            "status": "exited", "returncode": 1, "stdout": "",
            "stderr": "invalid opcode (revert_data=0x gas_used=99)",
        }
        status, _, _ = java_diff.parse_evm(record)
        self.assertEqual(status, "evm_failure")

    def test_mismatch_is_nonzero_and_has_single_case_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [case()])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools, "--case", "m1-add", "--stage", "m1",
                env_extra={"MOCK_EVM_MODE": "mismatch"},
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(report["cases"][0]["status"], "mismatch")
            replay = report["cases"][0]["replay_command"]
            self.assertIn("--case m1-add", replay)
            self.assertIn("current fixture sources", report["replay_note"])
            failures = (Path(tmp) / "artifacts/failures.txt").read_text(encoding="utf-8")
            self.assertIn("oracle=42 evm=43", failures)

    def test_evm_timeout_oog_revert_and_malformed_are_distinct(self):
        scenarios = {
            "timeout": "evm_timeout", "oog": "evm_oog",
            "revert": "evm_revert", "malformed": "evm_malformed",
        }
        for mode, expected in scenarios.items():
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                fixtures = FixtureTree(tmp, [case(timeout=0.1)])
                tools = MockTools(tmp)
                completed, report = self.run_runner(
                    tmp, fixtures.path, tools, "--stage", "m1",
                    env_extra={"MOCK_EVM_MODE": mode},
                )
                self.assertNotEqual(completed.returncode, 0)
                self.assertEqual(report["cases"][0]["status"], expected)
                if mode == "oog":
                    self.assertEqual(report["cases"][0]["gas_used"], 99)

    def test_runtime_hash_must_be_identical_across_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("add"), case("identity", method="identity", args=[7]),
            ])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools, "--stage", "m1", "--tier", "full",
                env_extra={"MOCK_EVM_MODE": "runtime-change"},
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(report["cases"][0]["status"], "pass")
            self.assertEqual(report["cases"][1]["status"], "harness_error")
            self.assertIn("runtime_sha256 differs", report["cases"][1]["detail"])

    def test_oracle_exception_failure_malformed_and_timeout_are_distinct(self):
        scenarios = {
            "exception": "oracle_exception", "failure": "oracle_failure",
            "malformed": "oracle_failure", "timeout": "oracle_timeout",
        }
        for mode, expected in scenarios.items():
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                fixtures = FixtureTree(tmp, [case(timeout=0.1)])
                tools = MockTools(tmp)
                completed, report = self.run_runner(
                    tmp, fixtures.path, tools, "--stage", "m1",
                    env_extra={"MOCK_JAVA_MODE": mode},
                )
                self.assertNotEqual(completed.returncode, 0)
                self.assertEqual(report["cases"][0]["status"], expected)
                self.assertNotIn("evm", report["cases"][0])

    def test_deterministic_fast_sampling_and_cumulative_stages(self):
        cases = [case("m1-smoke")]
        cases += [case(f"m1-{i:02d}", smoke=False) for i in range(25)]
        cases += [case("m2-smoke", stage="m2")]
        cases += [case("m2b-smoke", stage="m2b")]
        selected_a = java_diff.select_cases(cases, "m1", "fast", 56, None)
        selected_b = java_diff.select_cases(cases, "m1", "fast", 56, None)
        selected_c = java_diff.select_cases(cases, "m1", "fast", 57, None)
        self.assertEqual([x["id"] for x in selected_a], [x["id"] for x in selected_b])
        self.assertNotEqual([x["id"] for x in selected_a], [x["id"] for x in selected_c])
        self.assertEqual(len(selected_a), 21)
        self.assertEqual(
            [x["id"] for x in java_diff.select_cases(cases, "m2", "smoke", 56, None)],
            ["m1-smoke", "m2-smoke"],
        )
        self.assertEqual(
            [x["id"] for x in java_diff.select_cases(cases, "m2b", "smoke", 56, None)],
            ["m1-smoke", "m2-smoke", "m2b-smoke"],
        )
        self.assertEqual(
            [x["id"] for x in java_diff.select_cases(cases, "all", "smoke", 56, None)],
            ["m1-smoke", "m2-smoke", "m2b-smoke"],
        )
        parsed = java_diff.parser_for(Path("/tmp/repo")).parse_args([])
        self.assertEqual(parsed.stage, "m2b")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m1", "full", 56, "m2-smoke")

    def test_manifest_rejects_bool_duplicate_id_escape_and_empty_selection(self):
        bad_mutations = []
        bool_arg = case(); bool_arg["args"] = [True]
        bad_mutations.append(([bool_arg], "signed int32"))
        bad_mutations.append(([case("same"), case("same")], "duplicate case id"))
        escaped = case(); escaped["sources"] = ["../outside.java"]
        bad_mutations.append(([escaped], "escapes"))
        missing_exception = case(expected_kind="java_exception")
        del missing_exception["expected_exception"]
        bad_mutations.append(([missing_exception], "expected_exception"))
        invalid_exception = case(expected_kind="java_exception")
        invalid_exception["expected_exception"] = "ArithmeticException"
        bad_mutations.append(([invalid_exception], "fully-qualified"))
        value_with_exception = case()
        value_with_exception["expected_exception"] = "java.lang.ArithmeticException"
        bad_mutations.append(([value_with_exception], "only valid"))
        for cases, message in bad_mutations:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "outside.java").write_text("class Outside {}", encoding="utf-8")
                fixtures = FixtureTree(tmp, cases)
                with self.assertRaisesRegex(java_diff.HarnessError, message):
                    java_diff.load_manifest(fixtures.path)
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [case("not-smoke", smoke=False)])
            _, loaded, _ = java_diff.load_manifest(fixtures.path)
            with self.assertRaisesRegex(java_diff.HarnessError, "no cases selected"):
                java_diff.select_cases(loaded, "m1", "smoke", 56, None)

    @unittest.skipUnless(os.environ.get("JAVA_DIFF_REAL_EVM_BIN"),
                         "set JAVA_DIFF_REAL_EVM_BIN to run real javac/java + M1 CLI smoke")
    def test_real_m1_temporary_fixture_smoke(self):
        evm_bin = Path(os.environ["JAVA_DIFF_REAL_EVM_BIN"]).resolve()
        self.assertTrue(evm_bin.is_file(), evm_bin)
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [case("real-m1-add")])
            artifacts = Path(tmp) / "real-artifacts"
            command = [
                sys.executable, str(HERE / "java_diff.py"), "--fixtures", str(fixtures.path),
                "--artifacts", str(artifacts), "--evm-bin", str(evm_bin),
                "--stage", "m1", "--tier", "smoke",
            ]
            completed = subprocess.run(
                command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            report = json.loads((artifacts / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status_counts"], {"pass": 1})
            self.assertEqual(report["cases"][0]["oracle_value"], 42)
            self.assertEqual(report["cases"][0]["evm_value"], 42)


if __name__ == "__main__":
    unittest.main()
