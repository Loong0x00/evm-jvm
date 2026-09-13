#!/usr/bin/env python3
"""Build the isolated System.getSecurityManager candidate from parent-c24d374bc.

This only writes a fresh ignored build directory.  Parent sources are copied as
read-only evidence inputs; the candidate's System image is compiled from the
owned Java source below this directory.
"""
from pathlib import Path
import hashlib, json, os, re, shutil, subprocess, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PARENT = HERE.parent / "parent-c24d374bc"
JAVAC = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
RT = Path("/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar")
ADDRESS = "4d43534543555249545947455454455200000001"
DOMAIN = "MC-SECURITY-GETTER-PREFLIGHT1"


def run(args, *, cwd, env, log):
    with log.open("w") as output:
        subprocess.run([str(x) for x in args], cwd=cwd, env=env,
                       stdout=output, stderr=subprocess.STDOUT, check=True)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_candidate.py BUILD_DIR")
    out = Path(sys.argv[1]).resolve()
    if out.parent != ROOT / "build" or not out.name.startswith("java-diff-mc-security-getter-") or out.exists():
        raise SystemExit("BUILD_DIR must be a fresh build/java-diff-mc-security-getter-* directory")
    if not JAVAC.is_file() or not RT.is_file():
        raise SystemExit("pinned Java 8 compiler/runtime unavailable")
    if not PARENT.is_dir():
        raise SystemExit("missing pinned parent-c24d374bc evidence")
    out.mkdir(); (out / "tmp").mkdir()
    env = dict(os.environ, TMPDIR=str(out / "tmp"), PYTHONDONTWRITEBYTECODE="1",
               NODE_PATH=str(ROOT / "jvmevm/runtime/node_modules"))
    if not Path(env["TMPDIR"]).is_absolute():
        raise SystemExit("TMPDIR must be absolute")

    for part in ("engine", "coordinator"):
        shutil.copytree(PARENT / part, out / part)
    shutil.copytree(HERE / "bootstrap", out / "bootstrap")
    classes = out / "bootstrap-classes"
    classes.mkdir()
    run([JAVAC, "-source", "8", "-target", "8", "-g:none", "-bootclasspath", RT,
         "-d", classes, out / "bootstrap/java/lang/System.java"], cwd=ROOT, env=env,
        log=out / "bootstrap-build.log")
    system = (classes / "java/lang/System.class").read_bytes()
    (out / "bootstrap/java/lang/System.class.hex").write_text(system.hex() + "\n")
    (out / "bootstrap/pins.json").write_text(json.dumps({
        "javac": str(JAVAC), "release": 8,
        "images": [{"name": "java/lang/System", "bytes": len(system), "sha256": sha(system)}],
    }, indent=2) + "\n")

    engine = out / "engine/MCEntryInterpreter.sol"
    text = engine.read_text()
    pattern = r'(function _bootstrapSystem\(\) private pure returns \(bytes memory\) \{ return hex")([0-9a-f]+)("; \})'
    match = re.search(pattern, text)
    if not match:
        raise SystemExit("parent System bootstrap not found")
    parent_system = match.group(2)
    text, changed = re.subn(pattern, lambda m: m.group(1) + system.hex() + m.group(3), text)
    if changed != 1:
        raise SystemExit("System replacement was not unique")
    text = text.replace("MC-PROPERTIES-PARENT1", DOMAIN)
    engine.write_text(text)

    base = (PARENT / "engine/MCEntryInterpreter.sol").read_text()
    pat = r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
    old = dict(re.findall(pat, base)); new = dict(re.findall(pat, text))
    if len(old) != 48 or len(new) != 48 or old.get("_bootstrapSystem") != parent_system:
        raise SystemExit("unexpected parent bootstrap inventory")
    if any(old[name] != new[name] for name in old if name != "_bootstrapSystem"):
        raise SystemExit("a non-System bootstrap image changed")

    run(["node", out / "engine/build.js"], cwd=ROOT, env=env, log=out / "engine-build.log")
    engine_art = json.loads((out / "engine/MCEntryInterpreter.json").read_text())

    coordinator = out / "coordinator/MCEntryCoordinator.sol"
    ctext = coordinator.read_text().replace("MC-PROPERTIES-PARENT1", DOMAIN)
    ctext, n = re.subn(r'address private constant ENGINE = .*?;',
                       'address private constant ENGINE = address(bytes20(hex"' + ADDRESS + '"));', ctext)
    if n != 1:
        raise SystemExit("coordinator engine address replacement failed")
    parent_hash = "eb4c959c4893d83ef2a20918693f1ab499d812845a54b9377eba3615a8da1be7"
    ctext = ctext.replace(parent_hash, engine_art["codeHashes"]["runtimeKeccak256"])
    coordinator.write_text(ctext)
    run(["node", out / "coordinator/build.js"], cwd=ROOT, env=env, log=out / "coordinator-build.log")
    coord_art = json.loads((out / "coordinator/MCEntryCoordinator.json").read_text())

    # Exact, generated-fixture-only public EVM driver basis. It has no original
    # inputs in this preflight invocation; all immutable pins and domain strings
    # are rewritten before build.
    driver = (HERE.parent / "local-budget-1b/executed_driver.go.txt").read_text()
    replacements = {
        "877f35a4ac4092a7c65ab5071104413e4579ced0b69a172852db77d772aee1bb": engine_art["codeHashes"]["runtimeSHA256"],
        "0xeb4c959c4893d83ef2a20918693f1ab499d812845a54b9377eba3615a8da1be7": engine_art["codeHashes"]["runtimeKeccak256"],
        "0x4ac62a3ecc1612110cbc97779ebf760d101a33f1c85ddfb03c75d1b5478f2bae": coord_art["codeHashes"]["runtimeKeccak256"],
        "321590": str(len(engine_art["deployedBytecode"]) // 2),
        "3547": str(len(coord_art["deployedBytecode"]) // 2),
        "0x4d4350524f50455254494553504152454e540001": "0x" + ADDRESS,
        "MC-PROPERTIES-PARENT1": DOMAIN,
    }
    for old_value, new_value in replacements.items():
        if old_value not in driver:
            raise SystemExit("driver pin not found: " + old_value)
        driver = driver.replace(old_value, new_value)
    driver_path = out / "executed_generated_driver.go.txt"
    driver_path.write_text(driver)
    main_go = out / "main.go"; main_go.write_text(driver)
    run(["gofmt", "-w", main_go], cwd=ROOT, env=env, log=out / "gofmt.log")
    run(["go", "build", "-trimpath", "-o", out / "driver", main_go], cwd=ROOT, env=env, log=out / "driver-build.log")
    run(["go", "vet", main_go], cwd=ROOT, env=env, log=out / "driver-vet.log")

    pins = {
        "parent": "c24d374bc", "address": "0x" + ADDRESS, "domain": DOMAIN,
        "bootstrap": {"System": {"bytes": len(system), "sha256": sha(system)},
                      "otherBootstrapImagesIdentical": True, "bootstrapCount": len(new)},
        "engine": {"bytes": len(engine_art["deployedBytecode"]) // 2, **engine_art["codeHashes"]},
        "coordinator": {"bytes": len(coord_art["deployedBytecode"]) // 2, **coord_art["codeHashes"]},
        "limits": {"maxFrames": 128, "classInputs": 24, "classInputBytes": 262144,
                   "constantPool": 4096, "code": 65535, "runtimeBytesMax": 327680,
                   "externalLocalGas": 1000000000, "reserve": 25000000},
    }
    (out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
    print(json.dumps(pins, indent=2))


if __name__ == "__main__":
    main()
