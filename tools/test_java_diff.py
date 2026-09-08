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
    Class<?> c;
    try { c = Class.forName(a[0]); }
    catch (AbstractMethodError e) {
      System.out.println("exception=" + e.getClass().getName());
      return;
    }
    catch (IncompatibleClassChangeError e) {
      System.out.println("exception=" + e.getClass().getName());
      return;
    }
    catch (ExceptionInInitializerError | StackOverflowError e) {
      System.out.println("exception=" + e.getClass().getName());
      return;
    }
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
         expected_exception="java.lang.ArithmeticException", class_name="Arithmetic",
         sources=None, class_files=None):
    fixture = {
        "id": case_id,
        "stage": stage,
        "sources": ["Arithmetic.java"] if sources is None else sources,
        "class": class_name,
        "method": method,
        "args": [20, 22] if args is None else args,
        "gas_limit": 2_000_000,
        "timeout_seconds": timeout,
        "smoke": smoke,
        "expected_kind": expected_kind,
    }
    if expected_kind == "java_exception":
        fixture["expected_exception"] = expected_exception
    if class_files is not None:
        fixture["class_files"] = class_files
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
            import os, pathlib, re, sys
            if "-version" in sys.argv:
                print("javac mock-8")
                raise SystemExit(0)
            out = pathlib.Path(sys.argv[sys.argv.index("-d") + 1])
            out.mkdir(parents=True, exist_ok=True)
            emitted = []
            for arg in sys.argv:
                if arg.endswith(".java"):
                    source = pathlib.Path(arg)
                    text = source.read_text(encoding="utf-8")
                    match = re.search(r"(?m)^\s*package\s+([A-Za-z_$][A-Za-z0-9_$.]*)\s*;", text)
                    package = [] if match is None else match.group(1).split(".")
                    relative = pathlib.Path(*package, source.stem + ".class")
                    target = out / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if relative.as_posix() != os.environ.get("MOCK_JAVAC_OMIT"):
                        target.write_bytes(b"raw-class:" + relative.as_posix().encode())
                        emitted.append(target)
            link = os.environ.get("MOCK_JAVAC_SYMLINK")
            if link:
                target = out / link
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() or target.is_symlink():
                    target.unlink()
                target.symlink_to(os.environ["MOCK_JAVAC_SYMLINK_TARGET"])
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
            known = {
                "divide": "java.lang.ArithmeticException",
                "recurse": "java.lang.StackOverflowError",
                "initFail": "java.lang.ExceptionInInitializerError",
                "negativeArray": "java.lang.NegativeArraySizeException",
                "arrayBounds": "java.lang.ArrayIndexOutOfBoundsException",
                "nullArray": "java.lang.NullPointerException",
                "logicalOOM": "java.lang.OutOfMemoryError",
                "initArrayFailure": "java.lang.ExceptionInInitializerError",
                "initLogicalOOM": "java.lang.OutOfMemoryError",
                "nullField": "java.lang.NullPointerException",
                "objectOOM": "java.lang.OutOfMemoryError",
                "initObjectOOM": "java.lang.OutOfMemoryError",
                "badCast": "java.lang.ClassCastException",
                "initBadCast": "java.lang.ExceptionInInitializerError",
                "arrayStore": "java.lang.ArrayStoreException",
                "initArrayStore": "java.lang.ExceptionInInitializerError",
                "multiNegative": "java.lang.NegativeArraySizeException",
                "multiOOM": "java.lang.OutOfMemoryError",
                "initMultiNegative": "java.lang.ExceptionInInitializerError",
                "defaultConflict": "java.lang.IncompatibleClassChangeError",
                "missingDefault": "java.lang.AbstractMethodError",
                "initDefaultConflict": "java.lang.IncompatibleClassChangeError",
                "initMissingDefault": "java.lang.AbstractMethodError",
                "failedInitUse": "java.lang.NoClassDefFoundError",
            }
            if mode in ("exception", "root-init-eiie") or (
                    mode == "by-method" and method in known):
                if mode == "root-init-eiie":
                    default = "java.lang.ExceptionInInitializerError"
                else:
                    default = known.get(method, "java.lang.ArithmeticException")
                print("exception=" + os.environ.get("MOCK_JAVA_EXCEPTION", default))
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
            known = {
                "divide": "java.lang.ArithmeticException",
                "recurse": "java.lang.StackOverflowError",
                "initFail": "java.lang.ExceptionInInitializerError",
                "negativeArray": "java.lang.NegativeArraySizeException",
                "arrayBounds": "java.lang.ArrayIndexOutOfBoundsException",
                "nullArray": "java.lang.NullPointerException",
                "logicalOOM": "java.lang.OutOfMemoryError",
                "initArrayFailure": "java.lang.ExceptionInInitializerError",
                "initLogicalOOM": "java.lang.OutOfMemoryError",
                "nullField": "java.lang.NullPointerException",
                "objectOOM": "java.lang.OutOfMemoryError",
                "initObjectOOM": "java.lang.OutOfMemoryError",
                "badCast": "java.lang.ClassCastException",
                "initBadCast": "java.lang.ExceptionInInitializerError",
                "arrayStore": "java.lang.ArrayStoreException",
                "initArrayStore": "java.lang.ExceptionInInitializerError",
                "multiNegative": "java.lang.NegativeArraySizeException",
                "multiOOM": "java.lang.OutOfMemoryError",
                "initMultiNegative": "java.lang.ExceptionInInitializerError",
                "defaultConflict": "java.lang.IncompatibleClassChangeError",
                "missingDefault": "java.lang.AbstractMethodError",
                "initDefaultConflict": "java.lang.IncompatibleClassChangeError",
                "initMissingDefault": "java.lang.AbstractMethodError",
                "failedInitUse": "java.lang.NoClassDefFoundError",
            }
            exception_outcome = mode in ("exception", "exception-gasbad", "root-init-eiie")
            exception_outcome = exception_outcome or (
                mode == "by-method" and method in known)
            exception_outcome = exception_outcome or (
                mode == "exception-runtime-change" and method == "divide")
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
                if mode == "root-init-eiie":
                    default = "java.lang.ExceptionInInitializerError"
                else:
                    default = known.get(method, "java.lang.ArithmeticException")
                print("exception=" + os.environ.get("MOCK_EVM_EXCEPTION", default))
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
        # Class.forName can fail before Method.invoke. That genuine initializer
        # outcome must not be confused with an oracle process/configuration error.
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("m3c-root-init", stage="m3c", method="initFail", args=[],
                     expected_kind="java_exception",
                     expected_exception="java.lang.ExceptionInInitializerError"),
            ])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools,
                env_extra={
                    "MOCK_JAVA_MODE": "root-init-eiie",
                    "MOCK_EVM_MODE": "root-init-eiie",
                },
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = report["cases"][0]
            self.assertEqual(result["status"], "pass")
            self.assertEqual(
                result["oracle_exception"], "java.lang.ExceptionInInitializerError"
            )
            self.assertEqual(
                result["evm_exception"], "java.lang.ExceptionInInitializerError"
            )
            self.assertEqual(result["gas_used"], 456)
            self.assertEqual(report["runtime_sha256"], "a" * 64)

    def test_mixed_value_and_known_exceptions_share_runtime_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("value", method="identity", args=[7]),
                case("arithmetic", stage="m2b", method="divide", args=[7, 0],
                     expected_kind="java_exception"),
                case("stack-overflow", stage="m3a", method="recurse", args=[],
                     expected_kind="java_exception",
                     expected_exception="java.lang.StackOverflowError"),
                case("initializer-error", stage="m3c", method="initFail", args=[],
                     expected_kind="java_exception",
                     expected_exception="java.lang.ExceptionInInitializerError"),
                case("failed-init-use", stage="m5da", method="failedInitUse", args=[],
                     expected_kind="java_exception",
                     expected_exception="java.lang.NoClassDefFoundError"),
            ])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools, "--tier", "full",
                env_extra={"MOCK_JAVA_MODE": "by-method", "MOCK_EVM_MODE": "by-method"},
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(report["status_counts"], {"pass": 5})
            self.assertEqual(report["runtime_sha256"], "a" * 64)
            self.assertEqual(
                [result["runtime_sha256"] for result in report["cases"]], ["a" * 64] * 5
            )
            self.assertEqual(report["cases"][0]["evm_value"], 7)
            self.assertEqual(
                report["cases"][1]["evm_exception"], "java.lang.ArithmeticException"
            )
            self.assertEqual(
                report["cases"][2]["evm_exception"], "java.lang.StackOverflowError"
            )
            self.assertEqual(
                report["cases"][3]["evm_exception"],
                "java.lang.ExceptionInInitializerError",
            )
            self.assertEqual(
                report["cases"][4]["evm_exception"],
                "java.lang.NoClassDefFoundError",
            )

    def test_m4a_known_array_outcomes_match_by_exact_class(self):
        expected = {
            "negativeArray": "java.lang.NegativeArraySizeException",
            "arrayBounds": "java.lang.ArrayIndexOutOfBoundsException",
            "nullArray": "java.lang.NullPointerException",
            # Logical-cap OOM is deliberately mock-only: exhausting the host JVM
            # heap is neither safe nor equivalent to the EVM resource profile.
            "logicalOOM": "java.lang.OutOfMemoryError",
            "initArrayFailure": "java.lang.ExceptionInInitializerError",
            "initLogicalOOM": "java.lang.OutOfMemoryError",
        }
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("m4a-" + method, stage="m4a", method=method, args=[],
                     expected_kind="java_exception", expected_exception=exception)
                for method, exception in expected.items()
            ])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools, "--stage", "m4a", "--tier", "full",
                env_extra={"MOCK_JAVA_MODE": "by-method", "MOCK_EVM_MODE": "by-method"},
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(report["status_counts"], {"pass": len(expected)})
            self.assertEqual(
                [result["evm_exception"] for result in report["cases"]],
                list(expected.values()),
            )

    def test_m4a_oom_is_not_wrapped_and_oog_is_not_an_oom(self):
        fixture_case = case(
            "m4a-init-oom", stage="m4a", method="initLogicalOOM", args=[],
            expected_kind="java_exception", expected_exception="java.lang.OutOfMemoryError",
        )
        scenarios = [
            ("by-method", {}, 0, "pass"),
            ("by-method", {"MOCK_EVM_EXCEPTION": "java.lang.ExceptionInInitializerError"},
             1, "mismatch"),
            ("oog", {}, 1, "evm_oog"),
        ]
        for mode, extra, returncode, status in scenarios:
            with self.subTest(mode=mode, extra=extra), tempfile.TemporaryDirectory() as tmp:
                fixtures = FixtureTree(tmp, [fixture_case])
                tools = MockTools(tmp)
                completed, report = self.run_runner(
                    tmp, fixtures.path, tools,
                    env_extra={
                        "MOCK_JAVA_MODE": "by-method", "MOCK_EVM_MODE": mode, **extra,
                    },
                )
                self.assertEqual(completed.returncode == 0, returncode == 0)
                self.assertEqual(report["cases"][0]["status"], status)
                if mode == "oog":
                    self.assertNotIn("evm_exception", report["cases"][0])

    def test_m4b_object_outcomes_keep_exact_classes_and_oog_distinct(self):
        expected = {
            "nullField": "java.lang.NullPointerException",
            # Fixed interpreter caps are mock-only; never force host JVM OOM.
            "objectOOM": "java.lang.OutOfMemoryError",
            "initObjectOOM": "java.lang.OutOfMemoryError",
        }
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("m4b-" + method, stage="m4b", method=method, args=[],
                     expected_kind="java_exception", expected_exception=exception)
                for method, exception in expected.items()
            ])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools, "--stage", "m4b", "--tier", "full",
                env_extra={"MOCK_JAVA_MODE": "by-method", "MOCK_EVM_MODE": "by-method"},
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(report["status_counts"], {"pass": 3})
            self.assertEqual(
                [item["evm_exception"] for item in report["cases"]], list(expected.values())
            )

        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [case(
                "m4b-object-oog", stage="m4b", method="objectOOM", args=[],
                expected_kind="java_exception", expected_exception="java.lang.OutOfMemoryError",
            )])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools,
                env_extra={"MOCK_JAVA_MODE": "by-method", "MOCK_EVM_MODE": "oog"},
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(report["cases"][0]["status"], "evm_oog")
            self.assertNotIn("evm_exception", report["cases"][0])

    def test_m4d_and_m4e_array_outcomes_are_exact(self):
        # M4e adds no kind: multidimensional NASE/OOM remain exact kinds 4/7,
        # while initializer failures remain kind 3. Kinds 8 and 9 stay exact.
        expected = {
            "badCast": "java.lang.ClassCastException",
            "initBadCast": "java.lang.ExceptionInInitializerError",
            "arrayStore": "java.lang.ArrayStoreException",
            "initArrayStore": "java.lang.ExceptionInInitializerError",
        }
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("m4d-" + method, stage="m4d", method=method, args=[],
                     expected_kind="java_exception", expected_exception=exception)
                for method, exception in expected.items()
            ])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools, "--stage", "m4d", "--tier", "full",
                env_extra={"MOCK_JAVA_MODE": "by-method", "MOCK_EVM_MODE": "by-method"},
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(report["status_counts"], {"pass": 4})
            self.assertEqual(
                [item["evm_exception"] for item in report["cases"]], list(expected.values())
            )

        m4e_expected = {
            "multiNegative": "java.lang.NegativeArraySizeException",
            # Logical interpreter quota is mock-only; never exhaust host JVM memory.
            "multiOOM": "java.lang.OutOfMemoryError",
            "initMultiNegative": "java.lang.ExceptionInInitializerError",
        }
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("m4e-" + method, stage="m4e", method=method, args=[],
                     expected_kind="java_exception", expected_exception=exception)
                for method, exception in m4e_expected.items()
            ])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools, "--stage", "m4e", "--tier", "full",
                env_extra={"MOCK_JAVA_MODE": "by-method", "MOCK_EVM_MODE": "by-method"},
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(report["status_counts"], {"pass": 3})
            self.assertEqual(
                [item["evm_exception"] for item in report["cases"]],
                list(m4e_expected.values()),
            )

        scenarios = [
            ("by-method", {"MOCK_EVM_EXCEPTION": "java.lang.NullPointerException"}, "mismatch"),
            ("oog", {}, "evm_oog"),
        ]
        for method, exception in (
            ("badCast", "java.lang.ClassCastException"),
            ("arrayStore", "java.lang.ArrayStoreException"),
        ):
            for mode, extra, want_status in scenarios:
                with self.subTest(method=method, mode=mode), tempfile.TemporaryDirectory() as tmp:
                    fixtures = FixtureTree(tmp, [case(
                        "m4d-exact", stage="m4d", method=method, args=[],
                        expected_kind="java_exception", expected_exception=exception,
                    )])
                    tools = MockTools(tmp)
                    completed, report = self.run_runner(
                        tmp, fixtures.path, tools,
                        env_extra={
                            "MOCK_JAVA_MODE": "by-method", "MOCK_EVM_MODE": mode, **extra,
                        },
                    )
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertEqual(report["cases"][0]["status"], want_status)
                    if mode == "oog":
                        self.assertNotIn("evm_exception", report["cases"][0])

    def test_m4d_unknown_exception_protocol_is_never_accepted(self):
        record = {
            "status": "exited", "returncode": 0, "stderr": "",
            "stdout": (
                "engine=evm-jvm-subset-interpreter\nruntime_bytes=123\n"
                + "runtime_sha256=" + "a" * 64
                + "\nexception=java.lang.UnsupportedOperationException\ngas_used=1\n"
            ),
        }
        status, values, detail = java_diff.parse_evm(record)
        self.assertEqual(status, "evm_malformed")
        self.assertEqual(values, {})
        self.assertIn("known supported", detail)
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [case(
                "unknown", stage="m4d", expected_kind="java_exception",
                expected_exception="java.lang.UnsupportedOperationException",
            )])
            with self.assertRaisesRegex(java_diff.HarnessError, "known supported"):
                java_diff.load_manifest(fixtures.path)

    def test_m4fb_linkage_errors_are_exact_known_outcomes_and_oog_stays_distinct(self):
        expected = {
            "defaultConflict": "java.lang.IncompatibleClassChangeError",
            "missingDefault": "java.lang.AbstractMethodError",
            "initDefaultConflict": "java.lang.IncompatibleClassChangeError",
            "initMissingDefault": "java.lang.AbstractMethodError",
        }
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("m4fb-" + method, stage="m4fb", method=method, args=[],
                     expected_kind="java_exception", expected_exception=exception)
                for method, exception in expected.items()
            ])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools, "--stage", "m4fb", "--tier", "full",
                env_extra={"MOCK_JAVA_MODE": "by-method", "MOCK_EVM_MODE": "by-method"},
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(report["status_counts"], {"pass": 4})
            self.assertEqual(
                [result["evm_exception"] for result in report["cases"]],
                list(expected.values()),
            )

        for method, exception in (
            ("defaultConflict", "java.lang.IncompatibleClassChangeError"),
            ("missingDefault", "java.lang.AbstractMethodError"),
        ):
            with self.subTest(method=method), tempfile.TemporaryDirectory() as tmp:
                fixtures = FixtureTree(tmp, [case(
                    "m4fb-oog-" + method, stage="m4fb", method=method, args=[],
                    expected_kind="java_exception", expected_exception=exception,
                )])
                tools = MockTools(tmp)
                completed, report = self.run_runner(
                    tmp, fixtures.path, tools,
                    env_extra={"MOCK_JAVA_MODE": "by-method", "MOCK_EVM_MODE": "oog"},
                )
                self.assertNotEqual(completed.returncode, 0)
                self.assertEqual(report["cases"][0]["status"], "evm_oog")
                self.assertNotIn("evm_exception", report["cases"][0])

    def test_m4fb_exception_decoder_rejects_unknown_and_noncanonical_protocol(self):
        for exception in (
            "java.lang.LinkageError", "IncompatibleClassChangeError", "java.lang.AME",
        ):
            with self.subTest(exception=exception):
                record = {
                    "status": "exited", "returncode": 0, "stderr": "",
                    "stdout": (
                        "engine=evm-jvm-subset-interpreter\nruntime_bytes=123\n"
                        + "runtime_sha256=" + "a" * 64
                        + "\nexception=" + exception + "\ngas_used=1\n"
                    ),
                }
                status, values, _ = java_diff.parse_evm(record)
                self.assertEqual(status, "evm_malformed")
                self.assertEqual(values, {})

    def test_real_jvm_class_cast_matches_mock_evm(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [case(
                "m4c-real-cce", stage="m4c", method="badCast", args=[],
                expected_kind="java_exception",
                expected_exception="java.lang.ClassCastException",
            )])
            (fixtures.path / "Arithmetic.java").write_text("""
public final class Arithmetic {
  static class A {} static class B {}
  public static int badCast() { Object value = new A(); return ((B)value) == null ? 0 : 1; }
}
""", encoding="utf-8")
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools, "--stage", "m4c",
                env_extra={"PATH": os.environ.get("PATH", ""), "MOCK_EVM_MODE": "by-method"},
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(report["cases"][0]["oracle_exception"], "java.lang.ClassCastException")
            self.assertEqual(report["cases"][0]["evm_exception"], "java.lang.ClassCastException")

    def test_real_jvm_array_exceptions_match_mock_evm_without_host_oom(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("m4a-real-negative", stage="m4a", method="negativeArray", args=[],
                     expected_kind="java_exception",
                     expected_exception="java.lang.NegativeArraySizeException"),
                case("m4a-real-bounds", stage="m4a", method="arrayBounds", args=[],
                     expected_kind="java_exception",
                     expected_exception="java.lang.ArrayIndexOutOfBoundsException"),
                case("m4a-real-null", stage="m4a", method="nullArray", args=[],
                     expected_kind="java_exception",
                     expected_exception="java.lang.NullPointerException"),
                case("m4d-real-store", stage="m4d", method="arrayStore", args=[],
                     expected_kind="java_exception",
                     expected_exception="java.lang.ArrayStoreException"),
            ])
            (fixtures.path / "Arithmetic.java").write_text("""
public final class Arithmetic {
  static class Base {} static final class Child extends Base {}
  public static int negativeArray() { return new int[-1].length; }
  public static int arrayBounds() { return (new int[1])[1]; }
  public static int nullArray() { int[] value = null; return value.length; }
  public static int arrayStore() { Base[] value = new Child[1]; value[0] = new Base(); return 1; }
}
""", encoding="utf-8")
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools, "--stage", "m4d", "--tier", "full",
                env_extra={
                    "PATH": os.environ.get("PATH", ""),
                    "MOCK_EVM_MODE": "by-method",
                },
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(report["status_counts"], {"pass": 4})
            self.assertEqual(
                [result["oracle_exception"] for result in report["cases"]],
                [
                    "java.lang.NegativeArraySizeException",
                    "java.lang.ArrayIndexOutOfBoundsException",
                    "java.lang.NullPointerException",
                    "java.lang.ArrayStoreException",
                ],
            )

    def test_expected_stack_overflow_does_not_accept_actual_oog(self):
        fixture_case = case(
            "stack-overflow", stage="m3c", method="recurse", args=[],
            expected_kind="java_exception",
            expected_exception="java.lang.StackOverflowError",
        )
        scenarios = [
            ("oog", {}, "evm_oog"),
            ("by-method", {"MOCK_EVM_EXCEPTION": "java.lang.ExceptionInInitializerError"},
             "mismatch"),
        ]
        for mode, environment, status in scenarios:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                fixtures = FixtureTree(tmp, [fixture_case])
                tools = MockTools(tmp)
                completed, report = self.run_runner(
                    tmp, fixtures.path, tools,
                    env_extra={
                        "MOCK_JAVA_MODE": "by-method", "MOCK_EVM_MODE": mode,
                        **environment,
                    },
                )
                self.assertNotEqual(completed.returncode, 0)
                result = report["cases"][0]
                self.assertEqual(result["status"], status)
                self.assertEqual(result["runtime_sha256"], "a" * 64)
                self.assertEqual(report["runtime_sha256"], "a" * 64)
                if mode == "oog":
                    self.assertNotIn("evm_exception", result)
                else:
                    self.assertEqual(
                        result["evm_exception"], "java.lang.ExceptionInInitializerError"
                    )

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

    def test_bundle_packaged_paths_order_argv_and_hash_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_case = case(
                "m3b-packaged", stage="m3b", class_name="bundle.Root",
                sources=["bundle/Root.java", "bundle/Helper.java"],
                class_files=["bundle/Helper.class", "bundle/Root.class"],
            )
            fixtures = FixtureTree(tmp, [bundle_case])
            package = fixtures.path / "bundle"
            package.mkdir()
            (package / "Root.java").write_text(
                "package bundle; public class Root { public static int add(int a, int b) { return Helper.add(a,b); } }",
                encoding="utf-8",
            )
            (package / "Helper.java").write_text(
                "package bundle; public class Helper { public static int add(int a, int b) { return a+b; } }",
                encoding="utf-8",
            )
            tools = MockTools(tmp)
            completed, report = self.run_runner(tmp, fixtures.path, tools, "--tier", "full")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = report["cases"][0]
            compiled = Path(report["run_directory"]) / "compiled"
            paths = [compiled / "bundle/Helper.class", compiled / "bundle/Root.class"]
            expected_argv = [
                str(tools.evm), "-class", str(paths[0]), "-class", str(paths[1]),
                "-entry-class", "bundle/Root", "-method", "add", "-args=20,22",
                "-gas", "2000000",
            ]
            self.assertEqual(result["class_path"], str(paths[1]))
            self.assertEqual(result["class_files"], ["bundle/Helper.class", "bundle/Root.class"])
            self.assertEqual(result["class_paths"], [str(path) for path in paths])
            self.assertEqual(result["entry_class"], "bundle/Root")
            self.assertEqual(result["evm_argv"], expected_argv)
            self.assertEqual(result["evm"]["argv"], expected_argv)
            hashes = result["class_file_sha256"]
            self.assertEqual([item["path"] for item in hashes], result["class_files"])
            self.assertEqual(
                [item["sha256"] for item in hashes],
                [java_diff.sha256_file(path) for path in paths],
            )
            self.assertEqual(result["class_sha256"], hashes[1]["sha256"])
            self.assertEqual(result["oracle"]["argv"][-4:], ["bundle.Root", "add", "20", "22"])

    def test_legacy_and_one_file_bundle_keep_protocol_and_runtime_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("legacy-value", method="identity", args=[7]),
                case("bundle-exception", stage="m3b", method="divide", args=[7, 0],
                     expected_kind="java_exception", class_files=["Arithmetic.class"]),
            ])
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools, "--tier", "full",
                env_extra={"MOCK_JAVA_MODE": "by-method", "MOCK_EVM_MODE": "by-method"},
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            legacy, bundle = report["cases"]
            self.assertNotIn("-entry-class", legacy["evm_argv"])
            self.assertEqual(legacy["evm_argv"].count("-class"), 1)
            self.assertEqual(bundle["evm_argv"].count("-class"), 1)
            self.assertEqual(
                bundle["evm_argv"][bundle["evm_argv"].index("-entry-class") + 1],
                "Arithmetic",
            )
            self.assertEqual(legacy["runtime_sha256"], "a" * 64)
            self.assertEqual(bundle["runtime_sha256"], "a" * 64)
            self.assertEqual(report["runtime_sha256"], "a" * 64)
            self.assertEqual(bundle["evm_exception"], "java.lang.ArithmeticException")

    def test_class_files_manifest_rejects_empty_duplicates_and_unsafe_paths(self):
        mutations = [
            ([], "nonempty array"),
            (["Arithmetic.class", "Arithmetic.class"], "duplicates"),
            (["/tmp/Arithmetic.class"], "relative .class path"),
            (["C:/tmp/Arithmetic.class"], "relative .class path"),
            (["../Arithmetic.class"], "traversal"),
            (["pkg/../Arithmetic.class"], "traversal"),
            (["pkg//Arithmetic.class"], "empty or traversal"),
            (["Arithmetic.java"], "end in .class"),
            ([7], "relative .class path"),
        ]
        for class_files, message in mutations:
            with self.subTest(class_files=class_files), tempfile.TemporaryDirectory() as tmp:
                fixtures = FixtureTree(tmp, [case(
                    "bad-bundle", stage="m3b", class_files=class_files,
                )])
                with self.assertRaisesRegex(java_diff.HarnessError, message):
                    java_diff.load_manifest(fixtures.path)

    def test_missing_bundle_output_fails_without_cli_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [case(
                "missing-output", stage="m3b",
                class_files=["Arithmetic.class", "Missing.class"],
            )])
            tools = MockTools(tmp)
            completed, report = self.run_runner(tmp, fixtures.path, tools)
            self.assertNotEqual(completed.returncode, 0)
            result = report["cases"][0]
            self.assertEqual(result["status"], "harness_error")
            self.assertIn("Missing.class", result["detail"])
            self.assertIn("missing", result["detail"])
            self.assertNotIn("evm", result)

    def test_bundle_symlink_escape_fails_without_invoking_oracle_or_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [case(
                "symlink-output", stage="m3b",
                class_files=["Arithmetic.class", "Escape.class"],
            )])
            outside = Path(tmp) / "outside.class"
            outside.write_bytes(b"not javac output")
            tools = MockTools(tmp)
            completed, report = self.run_runner(
                tmp, fixtures.path, tools,
                env_extra={
                    "MOCK_JAVAC_SYMLINK": "Escape.class",
                    "MOCK_JAVAC_SYMLINK_TARGET": str(outside),
                },
            )
            self.assertNotEqual(completed.returncode, 0)
            result = report["cases"][0]
            self.assertEqual(result["status"], "harness_error")
            self.assertIn("escapes", result["detail"])
            self.assertNotIn("oracle", result)
            self.assertNotIn("evm", result)

    def test_deterministic_fast_sampling_and_cumulative_stages(self):
        cases = [case("m1-smoke")]
        cases += [case(f"m1-{i:02d}", smoke=False) for i in range(25)]
        cases += [case("m2-smoke", stage="m2")]
        cases += [case("m2b-smoke", stage="m2b")]
        cases += [case("m3a-smoke", stage="m3a")]
        cases += [case("m3b-smoke", stage="m3b")]
        cases += [case("m3c-smoke", stage="m3c")]
        cases += [case("m3d-smoke", stage="m3d")]
        cases += [case("m4a-smoke", stage="m4a")]
        cases += [case("m4b-smoke", stage="m4b")]
        cases += [case("m4c-smoke", stage="m4c")]
        cases += [case("m4d-smoke", stage="m4d")]
        cases += [case("m4e-smoke", stage="m4e")]
        cases += [case("m4fa-smoke", stage="m4fa")]
        cases += [case("m4fb-smoke", stage="m4fb")]
        cases += [case("m4fc-smoke", stage="m4fc")]
        cases += [case("m5a-smoke", stage="m5a")]
        cases += [case("m5ba-smoke", stage="m5ba")]
        cases += [case("m5bb-smoke", stage="m5bb")]
        cases += [case("m5ca-smoke", stage="m5ca")]
        cases += [case("m5cb-smoke", stage="m5cb")]
        cases += [case("m5cc-smoke", stage="m5cc")]
        cases += [case("m5cd-smoke", stage="m5cd")]
        cases += [case("m5da-smoke", stage="m5da")]
        selected_a = java_diff.select_cases(cases, "m1", "fast", 56, None)
        selected_b = java_diff.select_cases(cases, "m1", "fast", 56, None)
        selected_c = java_diff.select_cases(cases, "m1", "fast", 57, None)
        self.assertEqual([x["id"] for x in selected_a], [x["id"] for x in selected_b])
        self.assertNotEqual([x["id"] for x in selected_a], [x["id"] for x in selected_c])
        self.assertEqual(len(selected_a), 21)
        expected = {
            "m1": ["m1-smoke"],
            "m2": ["m1-smoke", "m2-smoke"],
            "m2b": ["m1-smoke", "m2-smoke", "m2b-smoke"],
            "m3a": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke"],
            "m3b": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke"],
            "m3c": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke"],
            "m3d": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke"],
            "m4a": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke"],
            "m4b": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke"],
            "m4c": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke", "m4c-smoke"],
            "m4d": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke", "m4c-smoke", "m4d-smoke"],
            "m4e": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke", "m4c-smoke", "m4d-smoke", "m4e-smoke"],
            "m4fa": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke", "m4c-smoke", "m4d-smoke", "m4e-smoke", "m4fa-smoke"],
            "m4fb": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke", "m4c-smoke", "m4d-smoke", "m4e-smoke", "m4fa-smoke", "m4fb-smoke"],
            "m4fc": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke", "m4c-smoke", "m4d-smoke", "m4e-smoke", "m4fa-smoke", "m4fb-smoke", "m4fc-smoke"],
            "m5a": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke", "m4c-smoke", "m4d-smoke", "m4e-smoke", "m4fa-smoke", "m4fb-smoke", "m4fc-smoke", "m5a-smoke"],
            "m5ba": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke", "m4c-smoke", "m4d-smoke", "m4e-smoke", "m4fa-smoke", "m4fb-smoke", "m4fc-smoke", "m5a-smoke", "m5ba-smoke"],
            "m5bb": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke", "m4c-smoke", "m4d-smoke", "m4e-smoke", "m4fa-smoke", "m4fb-smoke", "m4fc-smoke", "m5a-smoke", "m5ba-smoke", "m5bb-smoke"],
            "m5ca": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke", "m4c-smoke", "m4d-smoke", "m4e-smoke", "m4fa-smoke", "m4fb-smoke", "m4fc-smoke", "m5a-smoke", "m5ba-smoke", "m5bb-smoke", "m5ca-smoke"],
            "m5cb": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke", "m4c-smoke", "m4d-smoke", "m4e-smoke", "m4fa-smoke", "m4fb-smoke", "m4fc-smoke", "m5a-smoke", "m5ba-smoke", "m5bb-smoke", "m5ca-smoke", "m5cb-smoke"],
            "m5cc": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke", "m4c-smoke", "m4d-smoke", "m4e-smoke", "m4fa-smoke", "m4fb-smoke", "m4fc-smoke", "m5a-smoke", "m5ba-smoke", "m5bb-smoke", "m5ca-smoke", "m5cb-smoke", "m5cc-smoke"],
            "m5cd": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke", "m4c-smoke", "m4d-smoke", "m4e-smoke", "m4fa-smoke", "m4fb-smoke", "m4fc-smoke", "m5a-smoke", "m5ba-smoke", "m5bb-smoke", "m5ca-smoke", "m5cb-smoke", "m5cc-smoke", "m5cd-smoke"],
            "m5da": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke", "m4c-smoke", "m4d-smoke", "m4e-smoke", "m4fa-smoke", "m4fb-smoke", "m4fc-smoke", "m5a-smoke", "m5ba-smoke", "m5bb-smoke", "m5ca-smoke", "m5cb-smoke", "m5cc-smoke", "m5cd-smoke", "m5da-smoke"],
            "all": ["m1-smoke", "m2-smoke", "m2b-smoke", "m3a-smoke", "m3b-smoke", "m3c-smoke", "m3d-smoke", "m4a-smoke", "m4b-smoke", "m4c-smoke", "m4d-smoke", "m4e-smoke", "m4fa-smoke", "m4fb-smoke", "m4fc-smoke", "m5a-smoke", "m5ba-smoke", "m5bb-smoke", "m5ca-smoke", "m5cb-smoke", "m5cc-smoke", "m5cd-smoke", "m5da-smoke"],
        }
        for stage, want in expected.items():
            with self.subTest(stage=stage):
                selected = java_diff.select_cases(cases, stage, "smoke", 56, None)
                self.assertEqual([x["id"] for x in selected], want)
        parsed = java_diff.parser_for(Path("/tmp/repo")).parse_args([])
        self.assertEqual(parsed.stage, "m5da")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m2b", "full", 56, "m3a-smoke")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m4a", "full", 56, "m4b-smoke")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m4b", "full", 56, "m4c-smoke")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m4c", "full", 56, "m4d-smoke")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m4d", "full", 56, "m4e-smoke")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m4e", "full", 56, "m4fa-smoke")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m4fa", "full", 56, "m4fb-smoke")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m4fb", "full", 56, "m4fc-smoke")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m4fc", "full", 56, "m5a-smoke")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m5a", "full", 56, "m5ba-smoke")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m5ba", "full", 56, "m5bb-smoke")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m5bb", "full", 56, "m5ca-smoke")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m5ca", "full", 56, "m5cb-smoke")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m5cb", "full", 56, "m5cc-smoke")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m5cc", "full", 56, "m5cd-smoke")
        with self.assertRaises(java_diff.HarnessError):
            java_diff.select_cases(cases, "m5cd", "full", 56, "m5da-smoke")
        with self.assertRaisesRegex(java_diff.HarnessError, "unknown stage"):
            java_diff.select_cases(cases, "m4f", "full", 56, None)

    def test_manifest_accepts_exact_m4b_through_m5da_stage_spellings(self):
        self.assertEqual(java_diff.SCHEMA_VERSION, 1)
        self.assertEqual(len(java_diff.KNOWN_JAVA_EXCEPTIONS), 12)
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = FixtureTree(tmp, [
                case("objects", stage="m4b"), case("dispatch", stage="m4c"),
                case("reference-arrays", stage="m4d"), case("multidimensional", stage="m4e"),
                case("interfaces", stage="m4fa"), case("defaults", stage="m4fb"),
                case("interface-statics", stage="m4fc"), case("narrow-primitives", stage="m5a"),
                case("scalar-long", stage="m5ba"), case("long-arrays", stage="m5bb"),
                case("variable-control-flow", stage="m5ca"),
                case("scalar-ieee", stage="m5cb"),
                case("ieee-arithmetic", stage="m5cc"),
                case("ieee-arrays", stage="m5cd"),
                case("exceptions", stage="m5da", expected_kind="java_exception",
                     expected_exception="java.lang.NoClassDefFoundError"),
            ])
            _, loaded, _ = java_diff.load_manifest(fixtures.path)
            self.assertEqual([item["stage"] for item in loaded], ["m4b", "m4c", "m4d", "m4e", "m4fa", "m4fb", "m4fc", "m5a", "m5ba", "m5bb", "m5ca", "m5cb", "m5cc", "m5cd", "m5da"])
        for malformed in ("M4fc", "m4-fc", "m4f", "M5a", "m5-a", "M5ba", "m5b-a", "M5bb", "m5b-b", "M5ca", "m5c-a", "M5cb", "m5c-b", "M5cc", "m5c-c", "M5cd", "m5c-d", "M5da", "m5d-a", "interface-statics"):
            with self.subTest(stage=malformed), tempfile.TemporaryDirectory() as tmp:
                fixtures = FixtureTree(tmp, [case("bad-stage", stage=malformed)])
                with self.assertRaisesRegex(java_diff.HarnessError, "stage must be"):
                    java_diff.load_manifest(fixtures.path)

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
