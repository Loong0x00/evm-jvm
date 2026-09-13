#!/usr/bin/env python3
"""Run generated Java 8 System getter controls through the public EVM driver."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
JAVA = "/usr/lib/jvm/java-8-openjdk/bin/java"
JAVAC = "/usr/lib/jvm/java-8-openjdk/bin/javac"
CALL_ERROR = "0xd631c3a4"


def call(out, label, args, env):
    log = out / (label + ".log")
    with log.open("w") as f:
        p = subprocess.run([str(x) for x in args], cwd=ROOT, env=env,
                           stdout=f, stderr=subprocess.STDOUT)
    (out / (label + ".process.json")).write_text(json.dumps({
        "exit": p.returncode, "command": [str(x) for x in args],
    }, indent=2) + "\n")
    if p.returncode:
        raise SystemExit(label + " failed; see " + str(log))


def make_zip(classes, output, class_name):
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        info = zipfile.ZipInfo(class_name + ".class", (1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, (classes / (class_name + ".class")).read_bytes())


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: run_generated.py BUILD_DIR RUN_DIR")
    build, out = map(lambda x: Path(x).resolve(), sys.argv[1:])
    if build.parent != ROOT / "build" or not build.name.startswith("java-diff-mc-security-getter-"):
        raise SystemExit("unexpected candidate build directory")
    if out.parent != ROOT / "build" or not out.name.startswith("java-diff-mc-security-getter-") or out.exists():
        raise SystemExit("RUN_DIR must be fresh build/java-diff-mc-security-getter-*")
    out.mkdir(); classes = out / "classes"; classes.mkdir(); (out / "tmp").mkdir()
    env = dict(os.environ, TMPDIR=str(out / "tmp"), PYTHONDONTWRITEBYTECODE="1",
               NODE_PATH="/home/user/evm-jvm/geth/jvmevm/runtime/node_modules",
               MC_ENTRY_BINDINGS="SecurityGetterProbe.class")
    call(out, "java8-compile", [JAVAC, "-g:none", "-d", classes,
         HERE / "fixtures/SecurityGetterProbe.java", HERE / "fixtures/SecuritySetterRefusal.java"], env)
    call(out, "java8-getter-oracle", [JAVA, "-cp", classes, "SecurityGetterProbe"], env)
    call(out, "java8-setter-oracle", [JAVA, "-cp", classes, "SecuritySetterRefusal"], env)
    make_zip(classes, out / "SecurityGetterProbe.zip", "SecurityGetterProbe")
    make_zip(classes, out / "SecuritySetterRefusal.zip", "SecuritySetterRefusal")

    coord, engine, driver = build / "coordinator/MCEntryCoordinator.json", build / "engine/MCEntryInterpreter.json", build / "driver"
    normal = []
    opaque = None
    equivalence = None
    for quantum in (1, 7, 4096):
        label = "getter-q" + str(quantum)
        world = out / label
        args = [world, coord, engine, out / "SecurityGetterProbe.zip", quantum]
        call(out, label + "-start", [driver, "setup-chain", *args], env)
        call(out, label + "-finish", [driver, "finish", *args], env)
        call(out, label + "-reopen", [driver, "verify", *args], env)
        head = json.loads((world / "durable-head.json").read_text())
        refusals = list((out / "reports" / label).glob("*refusal.json"))
        if refusals or head["lifecycle"] != 2 or head["outcome"] != 2 or head["javaKind"] != 0:
            raise SystemExit(label + " did not complete the generated null branch")
        checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
        if hashlib.sha256(checkpoint).hexdigest() != head["checkpointSHA256"]:
            raise SystemExit(label + " checkpoint hash")
        row = {"quantum": quantum, "epoch": head["epoch"], "java": head["jvmSteps"],
               "internal": head["internalSteps"], "machineRoot": head["machineRoot"],
               "checkpointSHA256": head["checkpointSHA256"], "opaqueSHA256": hashlib.sha256(checkpoint[280:]).hexdigest(),
               "maxCallMS": head["counters"]["maxCallMs"], "maxGas": head["counters"]["maxGas"]}
        if opaque is None:
            opaque, equivalence = checkpoint[280:], (row["java"], row["internal"], row["machineRoot"])
        elif checkpoint[280:] != opaque or (row["java"], row["internal"], row["machineRoot"]) != equivalence:
            raise SystemExit(label + " differs from q1 terminal machine/opaque state")
        normal.append(row)

    # This is deliberately executed, not silently omitted: it must remain an
    # honest missing-member CallError after the normal default-null branch.
    label = "setter-direct"
    env["MC_ENTRY_BINDINGS"] = "SecuritySetterRefusal.class"
    world = out / label
    args = [world, coord, engine, out / "SecuritySetterRefusal.zip", 4096]
    call(out, label + "-start", [driver, "setup-chain", *args], env)
    reports = list((out / "reports" / label).glob("*refusal.json"))
    if len(reports) != 1:
        raise SystemExit("unsupported setter did not produce exactly one refusal")
    refusal = json.loads(reports[0].read_text())
    if refusal["selector"] != CALL_ERROR or refusal["uint256Words"][0] != "3" or not refusal["rootUnchanged"]:
        raise SystemExit("unsupported setter was not an honest CallError(3,pc) refusal")

    # Canonical nested ABI/events/checkpoint/read receipts for all successful
    # q1/q7/direct getter slices; this verifier has no Java execution authority.
    call(out, "canonical", ["node", HERE.parent / "parent-f780f1a13/verify_receipts.js",
                             build, out, "getter-q1", "getter-q7", "getter-q4096"], env)
    summary = {"generatedOnly": True, "normal": normal,
               "unsupportedSetter": {"receipt": reports[0].name, "selector": refusal["selector"],
                                     "words": refusal["uint256Words"], "gas": refusal["gas"]}}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
