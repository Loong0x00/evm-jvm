#!/usr/bin/env python3
"""Run one generated Properties world through the public AS0->ZI0->DI0 path.

Outputs are intentionally fresh ignored build/java-diff-mc-properties-* trees.
It never opens original artifacts, injects decoded pages, or calls a private
StateDB/session API. One 20-minute deadline covers build and every child call.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DEADLINE_SECONDS = 20 * 60


def call(command, log, env, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise RuntimeError("whole 20-minute deadline expired")
    with log.open("ab") as out:
        subprocess.run(command, check=True, stdout=out, stderr=subprocess.STDOUT,
                       env=env, timeout=remaining)


def lifecycle(head):
    return json.loads(head.read_text())["lifecycle"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quantum", required=True, type=int)
    parser.add_argument("--probe", choices=("construction", "properties"), required=True)
    args = parser.parse_args()
    if args.quantum < 1 or args.quantum > 4096:
        raise SystemExit("quantum outside existing 1..4096 slice limit")
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = ROOT / "build" / ("java-diff-mc-properties-" + stamp + "-" + args.probe + "-q" + str(args.quantum))
    out.mkdir(parents=True)
    deadline = time.monotonic() + DEADLINE_SECONDS
    source = HERE / "driver" / "properties_bounded_driver.go.txt"
    driver_go = out / "properties_bounded_driver.go"
    driver = out / "properties-bounded-driver"
    shutil.copyfile(source, driver_go)
    env = os.environ.copy()
    env.pop("TMPDIR", None)  # never inherit a deleted compiler scratch path.
    env["MC_ENTRY_BINDINGS"] = ("PropertiesConstructionProbe.class" if args.probe == "construction"
                                else "PropertiesProbe.class")
    probe_name = env["MC_ENTRY_BINDINGS"]
    class_hex = HERE / "fixtures" / (probe_name + ".hex")
    archive = out / "fixture.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as z:
        z.writestr(probe_name, bytes.fromhex(class_hex.read_text().strip()))
    call(["go", "build", "-o", str(driver), str(driver_go)], out / "go-build.log", env, deadline)
    coordinator = HERE / "coordinator" / "MCEntryCoordinator.json"
    engine = HERE / "engine" / "MCEntryInterpreter.json"
    world = out / "world"
    common = [str(world), str(coordinator), str(engine), str(archive), str(args.quantum)]
    call([str(driver), "setup-chain", *common], out / "setup.log", env, deadline)
    for _ in range(4096):
        if lifecycle(world / "durable-head.json") != 1:
            break
        call([str(driver), "resume-one", *common], out / "resume.log", env, deadline)
    else:
        raise RuntimeError("4096 resume guard reached")
    call([str(driver), "verify", *common], out / "verify.log", env, deadline)
    head = json.loads((world / "durable-head.json").read_text())
    if head["lifecycle"] != 2 or head["stage"] != "final-reopened":
        raise RuntimeError("generated guest did not reach canonical VOID terminal lifecycle")
    (out / "summary.json").write_text(json.dumps({
        "probe": args.probe, "quantum": args.quantum,
        "lifecycle": head["lifecycle"], "epoch": head["epoch"],
        "machineRoot": head["machineRoot"], "vfsRoot": head["vfsRoot"],
        "checkpointRoot": head["checkpointRoot"], "jvmSteps": head["jvmSteps"],
        "internalSteps": head["internalSteps"], "counters": head["counters"],
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
