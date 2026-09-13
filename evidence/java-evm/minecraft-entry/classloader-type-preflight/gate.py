#!/usr/bin/env python3
"""One-group source-only generated-fixture preflight for ClassLoader type only."""
from pathlib import Path
import hashlib, json, os, re, shutil, signal, subprocess, sys, time, zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASIS = HERE.parent / "parent-a30955bb0"
OUT_PREFIX = "java-diff-mc-classloader-type-"
JAVAC = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
JAVA = Path("/usr/lib/jvm/java-8-openjdk/bin/java")
RT = Path("/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar")
DOMAIN = "MC-CLASSLOADER-TYPE-PREFLIGHT1"
ADDRESS = "4d432d434c4153534c4f414445522d5459504501"  # bytes20("MC-CLASSLOADER-TYPE")
OWNER = "0x4d43434c4153534c4f414445522d4f574e455202"
OTHER = "0x4d43434c4153534c4f414445522d4f5448455203"
LIMIT_SECONDS = 20 * 60
LIMIT_RSS_KIB = 4 * 1024 * 1024
STARTED = time.monotonic()


def sha(data): return hashlib.sha256(data).hexdigest()

def replace_once(text, old, new, label):
    if text.count(old) != 1: raise RuntimeError("expected one " + label)
    return text.replace(old, new)

def group_rss_kib():
    pgid, total = os.getpgrp(), 0
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            fields = dict(x.split(":", 1) for x in (proc / "status").read_text().splitlines() if ":" in x)
            if int(fields.get("NSpgid", "-1").split()[0]) == pgid:
                total += int(fields.get("VmRSS", "0 kB").split()[0])
        except (OSError, ValueError): pass
    return total

def run(out, label, args, env):
    log, peak = out / (label + ".log"), 0
    with log.open("w") as f:
        p = subprocess.Popen([str(x) for x in args], cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT)
        while p.poll() is None:
            peak = max(peak, group_rss_kib())
            elapsed = time.monotonic() - STARTED
            if elapsed > LIMIT_SECONDS or peak > LIMIT_RSS_KIB:
                why = "whole-group-timeout" if elapsed > LIMIT_SECONDS else "whole-group-rss"
                (out / "watchdog.json").write_text(json.dumps({"reason": why, "peakRSSKiB": peak, "limitSeconds": LIMIT_SECONDS, "limitRSSKiB": LIMIT_RSS_KIB}, indent=2) + "\n")
                os.killpg(os.getpgrp(), signal.SIGKILL)
            time.sleep(.02)
        code = p.wait()
    (out / (label + ".watchdog.json")).write_text(json.dumps({"exit": code, "peakRSSKiB": peak, "elapsedMS": int((time.monotonic()-STARTED)*1000), "wholeGroupLimitSeconds": LIMIT_SECONDS, "wholeGroupRSSKiB": LIMIT_RSS_KIB}, indent=2) + "\n")
    if code: raise RuntimeError(label + " failed; see " + str(log))

def images(source):
    return dict(re.findall(r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";', source))

def deterministic_zip(classes, out, names):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in names:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, (classes / name).read_bytes())

def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)

def archive(out, normal, refusals, pins):
    target = HERE / "artifacts"
    if target.exists(): shutil.rmtree(target)
    for part, names in (("engine", ("MCEntryInterpreter.sol", "build.js", "MCEntryInterpreter.abi.json", "MCEntryInterpreter.init.hex", "MCEntryInterpreter.runtime.hex", "MCEntryInterpreter.json")), ("coordinator", ("MCEntryCoordinator.sol", "build.js", "MCEntryCoordinator.abi.json", "MCEntryCoordinator.init.hex", "MCEntryCoordinator.runtime.hex", "MCEntryCoordinator.json"))):
        for name in names: copy(out / part / name, target / part / name)
    copy(out / "bootstrap/java/lang/ClassLoader.java", target / "bootstrap/java/lang/ClassLoader.java")
    copy(out / "bootstrap/java/lang/ClassLoader.class.hex", target / "bootstrap/java/lang/ClassLoader.class.hex")
    copy(out / "executed_generated_driver.go.txt", target / "executed_generated_driver.go.txt")
    for p in out.glob("*.log"): copy(p, target / "logs" / p.name)
    for p in out.glob("*.watchdog.json"): copy(p, target / "logs" / p.name)
    for world in ("type-q1", "type-q7", "type-direct", "caller-replacement", "unsupported-get-system"):
        if (out / world).exists():
            for p in (out / world).rglob("*"):
                if p.is_file() and (p.name == "durable-head.json" or "checkpoints" in p.parts):
                    copy(p, target / "receipts" / world / p.relative_to(out / world))
        reports = out / "reports" / world
        if reports.exists():
            for p in reports.rglob("*"):
                if p.is_file(): copy(p, target / "receipts" / world / "reports" / p.relative_to(reports))
    (target / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
    (target / "results.json").write_text(json.dumps({"generatedOnly": True, "normal": normal, "refusals": refusals}, indent=2) + "\n")
    sums = [sha(p.read_bytes()) + "  " + str(p.relative_to(target)) for p in sorted(target.rglob("*")) if p.is_file()]
    (HERE / "SHA256SUMS").write_text("\n".join(sums) + "\n")

def main():
    if len(sys.argv) != 2: raise SystemExit("usage: gate.py absolute-fresh-build-dir")
    out = Path(sys.argv[1]).resolve()
    if out.parent != ROOT / "build" or not out.name.startswith(OUT_PREFIX) or out.exists():
        raise SystemExit("must use a fresh ignored build/java-diff-mc-classloader-type-* directory")
    if not all(x.is_file() for x in (JAVAC, JAVA, RT)): raise SystemExit("pinned Java 8 toolchain unavailable")
    for part in ("engine", "coordinator", "pins.json", "executed_driver.go.txt"):
        if not (BASIS / part).exists(): raise SystemExit("missing allowed parent basis " + part)
    out.mkdir(); (out / "tmp").mkdir()
    env = dict(os.environ, TMPDIR=str((out / "tmp").resolve()), NODE_PATH="/home/user/evm-jvm/geth/jvmevm/runtime/node_modules", PYTHONDONTWRITEBYTECODE="1")
    shutil.copytree(BASIS / "engine", out / "engine"); shutil.copytree(BASIS / "coordinator", out / "coordinator"); shutil.copytree(HERE / "bootstrap", out / "bootstrap")
    boot_classes = out / "bootstrap-classes"; boot_classes.mkdir()
    run(out, "bootstrap-build", [JAVAC, "-source", "8", "-target", "8", "-g:none", "-bootclasspath", RT, "-d", boot_classes, out / "bootstrap/java/lang/ClassLoader.java"], env)
    loader = (boot_classes / "java/lang/ClassLoader.class").read_bytes()
    if len(loader) == 0: raise RuntimeError("empty ClassLoader image")
    (out / "bootstrap/java/lang/ClassLoader.class.hex").write_text(loader.hex() + "\n")

    engine = out / "engine/MCEntryInterpreter.sol"; base = engine.read_text(); old = images(base)
    if len(old) != 49 or "_bootstrapClassLoader" in old: raise RuntimeError("parent must contain exactly 49 images")
    # The old profile string occurs in exactly the nine identity commitments, never only DBOOT.
    if base.count("MC-PRIVILEGED-ACTION-PARENT1") != 9: raise RuntimeError("expected nine parent engine domains")
    text = base.replace("MC-PRIVILEGED-ACTION-PARENT1", DOMAIN)
    text = replace_once(text, "bytes32[] memory h = new bytes32[](49);", "bytes32[] memory h = new bytes32[](50);", "bootstrap root length")
    text = replace_once(text, "        h[48] = keccak256(_bootstrapPrivilegedAction());\n        return keccak256(abi.encode(DBOOT, h));", "        h[48] = keccak256(_bootstrapPrivilegedAction());\n        h[49] = keccak256(_bootstrapClassLoader());\n        return keccak256(abi.encode(DBOOT, h));", "bootstrap append")
    text = replace_once(text, "                || _isReservedPropertiesClass(users[i]) || _isReservedPrivilegedActionClass(users[i])) {", "                || _isReservedPropertiesClass(users[i]) || _isReservedPrivilegedActionClass(users[i])\n                || _isReservedClassLoaderClass(users[i])) {", "caller replacement")
    text = replace_once(text, "uint256 count = inputCount + 43 + (suppliedObject ? 0 : 1)", "uint256 count = inputCount + 44 + (suppliedObject ? 0 : 1)", "class count")
    text = replace_once(text, "        p.classes[classSlot + 9].data = _bootstrapPrivilegedAction();\n        p.classClass = classSlot;", "        p.classes[classSlot + 9].data = _bootstrapPrivilegedAction();\n        p.classes[classSlot + 10].data = _bootstrapClassLoader();\n        p.classClass = classSlot;", "class append")
    marker = "    function _isReservedPropertiesClass(ClassInfo memory c) private pure returns (bool) {\n"
    helper = "    function _isReservedClassLoaderClass(ClassInfo memory c) private pure returns (bool) {\n        return _isNamedClass(c, bytes(\"java/lang/ClassLoader\"));\n    }\n\n"
    text = replace_once(text, marker, helper + marker, "ClassLoader reservation helper")
    marker = "    /// @dev Minimal Java 8 Properties family, compiled from the archived guest\n"
    function = "    /// @dev Exact minimal Java 8 java.lang.ClassLoader type with protected Object constructor only.\n    function _bootstrapClassLoader() private pure returns (bytes memory) { return hex\"" + loader.hex() + "\"; }\n\n"
    text = replace_once(text, marker, function + marker, "ClassLoader bootstrap")
    new = images(text)
    if len(new) != 50 or new.get("_bootstrapClassLoader") != loader.hex() or any(new.get(k) != v for k, v in old.items()): raise RuntimeError("prior49 bootstrap image drift")
    if text.count("_bootstrapClassLoader()") != 3: raise RuntimeError("ClassLoader bootstrap references")
    if text.count(DOMAIN) != 9 or "MC-PRIVILEGED-ACTION-PARENT1" in text: raise RuntimeError("engine domain isolation")
    engine.write_text(text)
    run(out, "engine-build", ["node", out / "engine/build.js"], env)
    ea = json.loads((out / "engine/MCEntryInterpreter.json").read_text())
    if len(ea["deployedBytecode"]) // 2 > 327680: raise RuntimeError("320KiB engine cap exceeded")

    coordinator = out / "coordinator/MCEntryCoordinator.sol"; ct = coordinator.read_text()
    if ct.count("MC-PRIVILEGED-ACTION-PARENT1") != 3: raise RuntimeError("coordinator domains")
    ct = ct.replace("MC-PRIVILEGED-ACTION-PARENT1", DOMAIN)
    ct = replace_once(ct, 'address private constant ENGINE = address(bytes20(hex"4d432d505249564143542d504152454e54310001"));', 'address private constant ENGINE = address(bytes20(hex"' + ADDRESS + '"));', "coordinator engine address")
    ct = replace_once(ct, "327a60e7a0a32a621291ed39875df8e9ef18be6dc37374fb6b5a9dbcf6435729", ea["codeHashes"]["runtimeKeccak256"], "coordinator engine hash")
    coordinator.write_text(ct)
    run(out, "coordinator-build", ["node", out / "coordinator/build.js"], env)
    ca = json.loads((out / "coordinator/MCEntryCoordinator.json").read_text())

    driver = (BASIS / "executed_driver.go.txt").read_text()
    replacements = {"MC-PRIVILEGED-ACTION-PARENT1": DOMAIN, "64f46d45d924e272ca74c0d73f652c68d00cc4709e36ff231483bdf62615c3c9": ea["codeHashes"]["runtimeSHA256"], "0x327a60e7a0a32a621291ed39875df8e9ef18be6dc37374fb6b5a9dbcf6435729": "0x" + ea["codeHashes"]["runtimeKeccak256"], "0xcf6c798d521a1280e2a42f2f34ee8dfd7e9659d93651bf13435d3e083881d224": "0x" + ca["codeHashes"]["runtimeKeccak256"], "323700": str(len(ea["deployedBytecode"]) // 2), "3547": str(len(ca["deployedBytecode"]) // 2), "0x4d432d505249564143542d504152454e54310001": "0x" + ADDRESS, "0x4d432d505249564143542d4f574e455200000002": OWNER, "0x4d432d505249564143542d4f5448455200000003": OTHER}
    for oldpin, newpin in replacements.items():
        if oldpin not in driver: raise RuntimeError("driver pin absent " + oldpin)
        driver = driver.replace(oldpin, newpin)
    (out / "executed_generated_driver.go.txt").write_text(driver); main_go = out / "main.go"; main_go.write_text(driver)
    run(out, "gofmt", ["gofmt", "-w", main_go], env); run(out, "driver-build", ["go", "build", "-trimpath", "-o", out / "driver", main_go], env); run(out, "driver-vet", ["go", "vet", main_go], env)

    classes = out / "classes"; classes.mkdir(); fixture = HERE / "fixtures"
    # Compile normal controls against rt.jar first. The caller-replacement class is
    # compiled separately, otherwise javac would resolve its same-package source
    # while compiling the honest unsupported-member control.
    sources = [fixture / "ClassLoaderTypeProbe.java", fixture / "ClassLoaderCallerReplacement.java", fixture / "ClassLoaderUnsupported.java"]
    run(out, "fixture-java8-build", [JAVAC, "-source", "8", "-target", "8", "-g:none", "-bootclasspath", RT, "-d", classes, *sources], env)
    run(out, "fixture-caller-replacement-build", [JAVAC, "-source", "8", "-target", "8", "-g:none", "-bootclasspath", RT, "-d", classes, fixture / "java/lang/ClassLoader.java"], env)
    run(out, "fixture-java8-oracle", [JAVA, "-cp", classes, "ClassLoaderTypeProbe"], env)
    deterministic_zip(classes, out / "type.zip", ["ClassLoaderTypeProbe.class", "ClassLoaderTypeProbe$MinimalLoader.class", "ClassLoaderTypeProbe$StringAction.class"])
    deterministic_zip(classes, out / "caller.zip", ["ClassLoaderCallerReplacement.class", "java/lang/ClassLoader.class"])
    deterministic_zip(classes, out / "unsupported.zip", ["ClassLoaderUnsupported.class"])

    normal, baseline = [], None
    for quantum, label in ((1, "type-q1"), (7, "type-q7"), (4096, "type-direct")):
        args = [out / label, out / "coordinator/MCEntryCoordinator.json", out / "engine/MCEntryInterpreter.json", out / "type.zip", quantum]
        env2 = dict(env, MC_ENTRY_BINDINGS="ClassLoaderTypeProbe.class,ClassLoaderTypeProbe$MinimalLoader.class,ClassLoaderTypeProbe$StringAction.class")
        run(out, label + "-start", [out / "driver", "setup-chain", *args], env2); run(out, label + "-finish", [out / "driver", "finish", *args], env2); run(out, label + "-reopen", [out / "driver", "verify", *args], env2)
        head = json.loads((out / label / "durable-head.json").read_text())
        if head["lifecycle"] != 2 or head["outcome"] != 2 or head["javaKind"] != 0: raise RuntimeError(label + " did not reach VOID")
        cp = (out / label / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes(); receipts = sorted((out / "reports" / label).glob("slice-*.json"))
        if sha(cp) != head["checkpointSHA256"] or not receipts or any(json.loads(p.read_text())["executionBudget"] != "LOCAL1B-USER-AUTHORIZED" for p in receipts): raise RuntimeError(label + " receipts")
        row = {"quantum": quantum, "epoch": head["epoch"], "java": head["jvmSteps"], "internal": head["internalSteps"], "machineRoot": head["machineRoot"], "checkpointSHA256": head["checkpointSHA256"], "opaqueSHA256": sha(cp[280:]), "maxGas": head["counters"]["maxGas"], "receiptCount": len(receipts)}
        value = (row["java"], row["internal"], row["machineRoot"], cp[280:])
        if baseline is None: baseline = value
        elif value != baseline: raise RuntimeError(label + " terminal machine/opaque differs")
        normal.append(row)

    refusals = {}
    # These selectors are the canonical raw ABI authority: BootstrapProfileError(1,1)
    # rejects caller replacement and CallError(3,0) reports absent static member.
    for label, archive_name, bindings, expected_selector in (("caller-replacement", "caller.zip", "ClassLoaderCallerReplacement.class,java/lang/ClassLoader.class", "0x6a23ad80"), ("unsupported-get-system", "unsupported.zip", "ClassLoaderUnsupported.class", "0xd631c3a4")):
        args = [out / label, out / "coordinator/MCEntryCoordinator.json", out / "engine/MCEntryInterpreter.json", out / archive_name, 4096]
        run(out, label + "-start", [out / "driver", "setup-chain", *args], dict(env, MC_ENTRY_BINDINGS=bindings))
        refusal = json.loads((out / "reports" / label / "start-refusal.json").read_text())
        if refusal.get("selector") != expected_selector or refusal["rootUnchanged"] is not True: raise RuntimeError(label + " refusal")
        refusals[label] = {"selector": refusal["selector"], "diagnostic": refusal.get("diagnostic"), "rootUnchanged": refusal["rootUnchanged"], "gas": refusal["gas"]}
    pins = {"parent": "parent-a30955bb0", "address": "0x" + ADDRESS, "owner": OWNER, "domain": DOMAIN, "bootstrap": {"ClassLoader": {"bytes": len(loader), "sha256": sha(loader)}, "prior49ImagesIdentical": True, "bootstrapCount": 50}, "engine": {"bytes": len(ea["deployedBytecode"]) // 2, **ea["codeHashes"]}, "coordinator": {"bytes": len(ca["deployedBytecode"]) // 2, **ca["codeHashes"]}, "limits": {"externalLocalGas": 1000000000, "reserve": 25000000, "callSeconds": 30, "wholeGroupSeconds": LIMIT_SECONDS, "wholeGroupRSSKiB": LIMIT_RSS_KIB, "classInputs": 24, "classInputBytes": 262144, "maxFrames": 128, "constantPool": 4096, "code": 65535, "checkpointBytes": 1048576, "headBytes": 32768, "engineBytesMax": 327680}}
    archive(out, normal, refusals, pins); print(json.dumps({"pins": pins, "normal": normal, "refusals": refusals}, indent=2))

if __name__ == "__main__": main()
