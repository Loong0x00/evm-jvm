#!/usr/bin/env python3
"""One-group source-only, generated-fixture preflight for PrivilegedAction."""
from pathlib import Path
import hashlib, json, os, re, shutil, signal, subprocess, sys, time, zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASIS = HERE.parent / "parent-2293e298e"
OUT_PREFIX = "java-diff-mc-privileged-action-"
JAVAC = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
JAVA = Path("/usr/lib/jvm/java-8-openjdk/bin/java")
JAVAP = Path("/usr/lib/jvm/java-8-openjdk/bin/javap")
RT = Path("/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar")
DOMAIN = "MC-PRIVILEGED-ACTION-PREFLIGHT1"
ADDRESS = "4d432d50524956494c454745442d414354494f4e"  # bytes20("MC-PRIVILEGED-ACTION")
OWNER = "0x4d4350524956414354494f4e0000000000000002"
OTHER = "0x4d4350524956414354494f4e0000000000000003"
LIMIT_SECONDS = 20 * 60
LIMIT_RSS_KIB = 4 * 1024 * 1024
STARTED = time.monotonic()


def sha(data): return hashlib.sha256(data).hexdigest()

def replace_once(text, old, new, label):
    if text.count(old) != 1:
        raise RuntimeError("expected one " + label)
    return text.replace(old, new)

def group_rss_kib():
    pgid = os.getpgrp(); total = 0
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            fields = dict(x.split(":", 1) for x in (proc / "status").read_text().splitlines() if ":" in x)
            if int(fields.get("NSpgid", "-1").split()[0]) == pgid:
                total += int(fields.get("VmRSS", "0 kB").split()[0])
        except (OSError, ValueError):
            pass
    return total

def run(out, label, args, env):
    log = out / (label + ".log"); peak = 0
    with log.open("w") as f:
        # No child session: all compiler, Java, Go and EVM descendants retain this one group.
        p = subprocess.Popen([str(x) for x in args], cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT)
        while p.poll() is None:
            peak = max(peak, group_rss_kib())
            if time.monotonic() - STARTED > LIMIT_SECONDS or peak > LIMIT_RSS_KIB:
                why = "whole-group-timeout" if time.monotonic() - STARTED > LIMIT_SECONDS else "whole-group-rss"
                (out / "watchdog.json").write_text(json.dumps({"reason": why, "peakRSSKiB": peak, "limitSeconds": LIMIT_SECONDS, "limitRSSKiB": LIMIT_RSS_KIB}, indent=2) + "\n")
                os.killpg(os.getpgrp(), signal.SIGKILL)
            time.sleep(0.02)
        code = p.wait()
    (out / (label + ".watchdog.json")).write_text(json.dumps({"exit": code, "peakRSSKiB": peak, "elapsedMS": int((time.monotonic()-STARTED)*1000), "wholeGroupLimitSeconds": LIMIT_SECONDS, "wholeGroupRSSKiB": LIMIT_RSS_KIB}, indent=2) + "\n")
    if code: raise RuntimeError(label + " failed; see " + str(log))

def bootstrap_images(source):
    pat = r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
    return dict(re.findall(pat, source))

def deterministic_zip(classes, out, names):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in names:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, (classes / name).read_bytes())

def copy_file(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dest)

def archive(out, rows, refusals, pins):
    archive_root = HERE / "artifacts"
    if archive_root.exists(): shutil.rmtree(archive_root)
    (archive_root / "engine").mkdir(parents=True)
    for part, names in (("engine", ("MCEntryInterpreter.sol", "build.js", "MCEntryInterpreter.abi.json", "MCEntryInterpreter.init.hex", "MCEntryInterpreter.runtime.hex", "MCEntryInterpreter.json")),
                        ("coordinator", ("MCEntryCoordinator.sol", "build.js", "MCEntryCoordinator.abi.json", "MCEntryCoordinator.init.hex", "MCEntryCoordinator.runtime.hex", "MCEntryCoordinator.json"))):
        for name in names: copy_file(out / part / name, archive_root / part / name)
    copy_file(out / "bootstrap/java/security/PrivilegedAction.java", archive_root / "bootstrap/java/security/PrivilegedAction.java")
    copy_file(out / "bootstrap/java/security/PrivilegedAction.class.hex", archive_root / "bootstrap/java/security/PrivilegedAction.class.hex")
    copy_file(out / "executed_generated_driver.go.txt", archive_root / "executed_generated_driver.go.txt")
    for log in out.glob("*.log"): copy_file(log, archive_root / "logs" / log.name)
    for watch in out.glob("*.watchdog.json"): copy_file(watch, archive_root / "logs" / watch.name)
    for world in [out / "probe-q1", out / "probe-q7", out / "probe-direct", out / "caller-replacement", out / "access-controller"]:
        if not world.exists(): continue
        for name in ("durable-head.json",):
            if (world / name).exists(): copy_file(world / name, archive_root / "receipts" / world.name / name)
        report_dir = out / "reports" / world.name
        if report_dir.exists(): shutil.copytree(report_dir, archive_root / "receipts" / world.name / "reports")
        if (world / "checkpoints").exists(): shutil.copytree(world / "checkpoints", archive_root / "receipts" / world.name / "checkpoints")
    (archive_root / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
    (archive_root / "results.json").write_text(json.dumps({"generatedOnly": True, "normal": rows, "refusals": refusals}, indent=2) + "\n")
    checks = []
    for p in sorted(x for x in archive_root.rglob("*") if x.is_file()): checks.append(sha(p.read_bytes()) + "  " + str(p.relative_to(archive_root)))
    (HERE / "SHA256SUMS").write_text("\n".join(checks) + "\n")

def main():
    if len(sys.argv) != 2: raise SystemExit("usage: gate.py absolute-fresh-build-dir")
    out = Path(sys.argv[1]).resolve()
    if out.parent != ROOT / "build" or not out.name.startswith(OUT_PREFIX) or out.exists():
        raise SystemExit("must use a fresh ignored build/java-diff-mc-privileged-action-* directory")
    if not all(x.is_file() for x in (JAVAC, JAVA, JAVAP, RT)): raise SystemExit("pinned Java 8 toolchain unavailable")
    for part in ("engine", "coordinator", "pins.json", "executed_driver.go.txt"):
        if not (BASIS / part).exists(): raise SystemExit("missing allowed parent basis " + part)
    out.mkdir(); (out / "tmp").mkdir()
    env = dict(os.environ, TMPDIR=str((out / "tmp").resolve()), NODE_PATH="/home/user/evm-jvm/geth/jvmevm/runtime/node_modules", PYTHONDONTWRITEBYTECODE="1")
    if not Path(env["TMPDIR"]).is_absolute(): raise RuntimeError("TMPDIR must be absolute")

    shutil.copytree(BASIS / "engine", out / "engine"); shutil.copytree(BASIS / "coordinator", out / "coordinator")
    shutil.copytree(HERE / "bootstrap", out / "bootstrap")
    boot_classes = out / "bootstrap-classes"; boot_classes.mkdir()
    run(out, "bootstrap-build", [JAVAC, "-source", "8", "-target", "8", "-g:none", "-bootclasspath", RT, "-d", boot_classes, out / "bootstrap/java/security/PrivilegedAction.java"], env)
    action = (boot_classes / "java/security/PrivilegedAction.class").read_bytes()
    if len(action) != 198 or sha(action) != "8188676e90fe79c605761b4592483b511966e7396f8a14e0d9b7962f00d948da": raise RuntimeError("PrivilegedAction image pin")
    (out / "bootstrap/java/security/PrivilegedAction.class.hex").write_text(action.hex() + "\n")

    engine = out / "engine/MCEntryInterpreter.sol"; base = engine.read_text(); old_images = bootstrap_images(base)
    if len(old_images) != 48 or "_bootstrapPrivilegedAction" in old_images: raise RuntimeError("parent must contain exactly 48 images")
    text = replace_once(base, 'keccak256("JVMEVM:MC-SECURITY-GETTER-PREFLIGHT1:BOOTSTRAP:1")', 'keccak256("JVMEVM:MC-PRIVILEGED-ACTION-PREFLIGHT1:BOOTSTRAP:1")', "bootstrap domain")
    text = replace_once(text, "bytes32[] memory h = new bytes32[](48);", "bytes32[] memory h = new bytes32[](49);", "bootstrap root length")
    text = replace_once(text, '        h[47] = keccak256(_bootstrapProperties());\n        return keccak256(abi.encode(DBOOT, h));', '        h[47] = keccak256(_bootstrapProperties());\n        h[48] = keccak256(_bootstrapPrivilegedAction());\n        return keccak256(abi.encode(DBOOT, h));', "bootstrap root append")
    text = replace_once(text, '                || _isReservedPlatformMapClass(users[i]) || _isReservedSystemClass(users[i])\n                || _isReservedPropertiesClass(users[i])) {', '                || _isReservedPlatformMapClass(users[i]) || _isReservedSystemClass(users[i])\n                || _isReservedPropertiesClass(users[i]) || _isReservedPrivilegedActionClass(users[i])) {', "caller replacement rejection")
    text = replace_once(text, 'uint256 count = inputCount + 42 + (suppliedObject ? 0 : 1)', 'uint256 count = inputCount + 43 + (suppliedObject ? 0 : 1)', "class count")
    text = replace_once(text, '        p.classes[classSlot + 8].data = _bootstrapProperties();\n        p.classClass = classSlot;', '        p.classes[classSlot + 8].data = _bootstrapProperties();\n        // Appended after the existing 48 pinned images; caller replacement is rejected.\n        p.classes[classSlot + 9].data = _bootstrapPrivilegedAction();\n        p.classClass = classSlot;', "class append")
    text = replace_once(text, '    function _isReservedSystemClass(ClassInfo memory c) private pure returns (bool) {\n        return _isNamedClass(c, bytes("java/lang/System"));\n    }\n', '    function _isReservedSystemClass(ClassInfo memory c) private pure returns (bool) {\n        return _isNamedClass(c, bytes("java/lang/System"));\n    }\n\n    function _isReservedPrivilegedActionClass(ClassInfo memory c) private pure returns (bool) {\n        return _isNamedClass(c, bytes("java/security/PrivilegedAction"));\n    }\n', "reserved interface helper")
    marker = '    /// @dev Minimal Java 8 Properties family, compiled from the archived guest\n'
    action_fn = '    /// @dev Exact Java 8 java.security.PrivilegedAction<T>; this interface grants no privilege.\n    function _bootstrapPrivilegedAction() private pure returns (bytes memory) { return hex"' + action.hex() + '"; }\n\n'
    text = replace_once(text, marker, action_fn + marker, "interface bootstrap")
    new_images = bootstrap_images(text)
    if len(new_images) != 49 or new_images.get("_bootstrapPrivilegedAction") != action.hex() or any(new_images.get(k) != v for k, v in old_images.items()):
        raise RuntimeError("bootstrap image drift")
    if text.count("_bootstrapPrivilegedAction()") != 3: raise RuntimeError("interface references")
    engine.write_text(text)
    run(out, "engine-build", ["node", out / "engine/build.js"], env)
    ea = json.loads((out / "engine/MCEntryInterpreter.json").read_text())

    coordinator = out / "coordinator/MCEntryCoordinator.sol"; ct = coordinator.read_text()
    ct = ct.replace("MC-SECURITY-GETTER-PREFLIGHT1", DOMAIN)
    ct = replace_once(ct, 'address private constant ENGINE = address(bytes20(hex"4d43534543555249545947455454455200000001"));', 'address private constant ENGINE = address(bytes20(hex"' + ADDRESS + '"));', "coordinator engine address")
    ct = replace_once(ct, "74609271d2d333b617e12d0c2ddeae2574b7812fc72f719453614acb3cc081ae", ea["codeHashes"]["runtimeKeccak256"], "coordinator engine hash")
    coordinator.write_text(ct)
    run(out, "coordinator-build", ["node", out / "coordinator/build.js"], env)
    ca = json.loads((out / "coordinator/MCEntryCoordinator.json").read_text())

    driver = (BASIS / "executed_driver.go.txt").read_text()
    replacements = {
        "MC-SECURITY-GETTER-PREFLIGHT1": DOMAIN,
        "4a8aafbfafef9fed3c3fd3106d99b9819a40ecc2eccfe40e234efa448dc038f9": ea["codeHashes"]["runtimeSHA256"],
        "0x74609271d2d333b617e12d0c2ddeae2574b7812fc72f719453614acb3cc081ae": "0x" + ea["codeHashes"]["runtimeKeccak256"],
        "0x113bcbc2b3512af2cbddc90379dbc8cacfb64f7df50ef7ec8f89e1bdfe8ed59a": "0x" + ca["codeHashes"]["runtimeKeccak256"],
        "322301": str(len(ea["deployedBytecode"]) // 2),
        "3547": str(len(ca["deployedBytecode"]) // 2),
        "0x4d43534543555249545947455454455200000001": "0x" + ADDRESS,
        "0x4d52304d41494e454e47494e4500000000000002": OWNER,
        "0x4d52304d41494e454e47494e4500000000000003": OTHER,
    }
    for old, new in replacements.items():
        if old not in driver: raise RuntimeError("driver pin absent " + old)
        driver = driver.replace(old, new)
    # Observer-only diagnostic field: preserve raw receipt bytes while recording the declared ABI error name.
    driver = replace_once(driver, '"error": fmt.Sprint(r.Err), "selector": selector(r.Out),', '"error": fmt.Sprint(r.Err), "errorName": errorName(engineABI, r.Out), "selector": selector(r.Out),', "failure receipt name")
    (out / "executed_generated_driver.go.txt").write_text(driver)
    main_go = out / "main.go"; main_go.write_text(driver)
    run(out, "gofmt", ["gofmt", "-w", main_go], env); run(out, "driver-build", ["go", "build", "-trimpath", "-o", out / "driver", main_go], env); run(out, "driver-vet", ["go", "vet", main_go], env)

    classes = out / "classes"; classes.mkdir()
    sources = [HERE / "fixtures/PrivilegedActionProbe.java", HERE / "fixtures/CallerPrivilegedActionRefusal.java", HERE / "fixtures/AccessControllerRefusal.java", HERE / "fixtures/java/security/PrivilegedAction.java"]
    run(out, "fixture-java8-build", [JAVAC, "-source", "8", "-target", "8", "-g:none", "-bootclasspath", RT, "-d", classes, *sources], env)
    run(out, "fixture-java8-oracle", [JAVA, "-cp", classes, "PrivilegedActionProbe"], env)
    run(out, "fixture-javap-bridge", [JAVAP, "-classpath", classes, "-p", "-s", "-c", "PrivilegedActionProbe$StringAction"], env)
    bridge_log = (out / "fixture-javap-bridge.log").read_text()
    if "public java.lang.String run();" not in bridge_log or "public java.lang.Object run();" not in bridge_log: raise RuntimeError("fixture lacks String/Object bridge")
    deterministic_zip(classes, out / "probe.zip", ["PrivilegedActionProbe.class", "PrivilegedActionProbe$StringAction.class"])
    deterministic_zip(classes, out / "caller.zip", ["CallerPrivilegedActionRefusal.class", "java/security/PrivilegedAction.class"])
    deterministic_zip(classes, out / "access.zip", ["AccessControllerRefusal.class"])

    rows = []; opaque = None; baseline = None
    for quantum, label in ((1, "probe-q1"), (7, "probe-q7"), (4096, "probe-direct")):
        e = dict(env, MC_ENTRY_BINDINGS="PrivilegedActionProbe.class,PrivilegedActionProbe$StringAction.class")
        args = [out / label, out / "coordinator/MCEntryCoordinator.json", out / "engine/MCEntryInterpreter.json", out / "probe.zip", quantum]
        run(out, label + "-start", [out / "driver", "setup-chain", *args], e); run(out, label + "-finish", [out / "driver", "finish", *args], e); run(out, label + "-reopen", [out / "driver", "verify", *args], e)
        head = json.loads((out / label / "durable-head.json").read_text())
        if head["lifecycle"] != 2 or head["outcome"] != 2 or head["javaKind"] != 0: raise RuntimeError(label + " did not reach genuine VOID")
        cp = (out / label / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
        if sha(cp) != head["checkpointSHA256"]: raise RuntimeError(label + " checkpoint digest")
        receipts = sorted((out / "reports" / label).glob("slice-*.json"))
        if not receipts or any(json.loads(p.read_text())["executionBudget"] != "LOCAL1B-USER-AUTHORIZED" for p in receipts): raise RuntimeError(label + " receipts")
        row = {"quantum": quantum, "epoch": head["epoch"], "java": head["jvmSteps"], "internal": head["internalSteps"], "machineRoot": head["machineRoot"], "checkpointSHA256": head["checkpointSHA256"], "opaqueSHA256": sha(cp[280:]), "maxGas": head["counters"]["maxGas"], "receiptCount": len(receipts)}
        current = (row["java"], row["internal"], row["machineRoot"], cp[280:])
        if baseline is None: baseline = current; opaque = cp[280:]
        elif current != baseline: raise RuntimeError(label + " terminal VOID/machine/opaque differs")
        rows.append(row)

    refusals = {}
    for label, fixture, bindings, expected in (("caller-replacement", "caller.zip", "CallerPrivilegedActionRefusal.class,java/security/PrivilegedAction.class", "BootstrapProfileError"), ("access-controller", "access.zip", "AccessControllerRefusal.class", "MCEntryMissingClass")):
        e = dict(env, MC_ENTRY_BINDINGS=bindings)
        args = [out / label, out / "coordinator/MCEntryCoordinator.json", out / "engine/MCEntryInterpreter.json", out / fixture, 4096]
        run(out, label + "-start", [out / "driver", "setup-chain", *args], e)
        refusal = json.loads((out / "reports" / label / "start-refusal.json").read_text())
        if refusal.get("errorName") != expected or refusal["rootUnchanged"] is not True:
            raise RuntimeError(label + " did not preserve the canonical honest refusal")
        # The raw receipt is the authority for the deliberately missing class.
        refusals[label] = {"selector": refusal["selector"], "diagnostic": refusal.get("diagnostic"), "rootUnchanged": refusal["rootUnchanged"], "gas": refusal["gas"]}
    if refusals["access-controller"]["diagnostic"] is None or refusals["access-controller"]["diagnostic"].get("name") != "java/security/AccessController": raise RuntimeError("AccessController was not honestly missing")

    pins = {"parent": "parent-2293e298e", "address": "0x" + ADDRESS, "owner": OWNER, "domain": DOMAIN, "bootstrap": {"PrivilegedAction": {"bytes": len(action), "sha256": sha(action)}, "prior48ImagesIdentical": True, "bootstrapCount": 49}, "engine": {"bytes": len(ea["deployedBytecode"]) // 2, **ea["codeHashes"]}, "coordinator": {"bytes": len(ca["deployedBytecode"]) // 2, **ca["codeHashes"]}, "limits": {"externalLocalGas": 1000000000, "reserve": 25000000, "callSeconds": 30, "wholeGroupSeconds": LIMIT_SECONDS, "wholeGroupRSSKiB": LIMIT_RSS_KIB, "classInputs": 24, "classInputBytes": 262144, "maxFrames": 128, "constantPool": 4096, "code": 65535, "checkpointBytes": 1048576, "headBytes": 32768, "engineBytesMax": 327680}}
    archive(out, rows, refusals, pins)
    print(json.dumps({"pins": pins, "normal": rows, "refusals": refusals}, indent=2))

if __name__ == "__main__": main()
