#!/usr/bin/env python3
"""Reproduce the minimal candidate's fixed LOCAL384 compile blocker."""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parents[3]


def run_logged(label, command, cwd, env, output):
    log = output / (label + ".log")
    with log.open("w") as stream:
        proc = subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                              stderr=subprocess.STDOUT, text=True)
    return proc.returncode, log


if len(sys.argv) != 2:
    raise SystemExit("usage: build_candidate.py build/java-diff-mc-array-list-int-constructor-NAME")
out = Path(sys.argv[1]).resolve()
assert out.parent == ROOT / "build"
assert out.name.startswith("java-diff-mc-array-list-int-constructor-")
assert not out.exists(), "refusing to overwrite prior build evidence"
out.mkdir(parents=True)
(out / "tmp").mkdir()
(out / "engine").mkdir()
env = dict(os.environ)
env.update({
    "TMPDIR": str(out / "tmp"),
    "NODE_PATH": str(ROOT / "jvmevm/runtime/node_modules"),
    "npm_config_offline": "true",
    "PYTHONDONTWRITEBYTECODE": "1",
})

code, source_log = run_logged(
    "source-verification", [sys.executable, STAGE / "tools/verify_source.py"], ROOT, env, out
)
if code:
    raise SystemExit(f"source verification failed; see {source_log}")
shutil.copy2(STAGE / "engine/MCEntryInterpreter.sol", out / "engine/MCEntryInterpreter.sol")
shutil.copy2(STAGE / "engine/build.js", out / "engine/build.js")
code, build_log = run_logged(
    "engine-compile", ["node", out / "engine/build.js"], ROOT, env, out
)
text = build_log.read_text(errors="replace")
match = re.search(r"runtime (\d+) bytes exceeds fixed LOCAL384 cap (\d+) bytes", text)
if code == 0 or not match:
    print(text[-12000:])
    raise SystemExit(f"expected a fixed-cap blocker; compiler exit={code}; log={build_log}")
actual, cap = map(int, match.groups())
assert actual == 394435, actual
assert cap == 393216, cap
result = {
    "result": "blocked",
    "runtimeBytes": actual,
    "fixedRuntimeCapBytes": cap,
    "overCapBytes": actual - cap,
    "engineCompileExit": code,
    "sourceLog": str(source_log),
    "compileLog": str(build_log),
    "artifactsWritten": False,
}
(out / "blocker.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
raise SystemExit(2)
