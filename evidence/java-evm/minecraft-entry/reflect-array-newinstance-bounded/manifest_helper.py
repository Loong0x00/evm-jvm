"""Regenerate the candidate-only SHA-256 inventory; no external inputs are read."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).parent
BASE = ROOT.parent / "reflect-array-source-base-p52"
sha = lambda b: hashlib.sha256(b).hexdigest()
pins = json.loads((ROOT / "candidate-pins.json").read_text())
files = []
for path in sorted(ROOT.rglob("*")):
    if not path.is_file() or path.name == "source-manifest.json":
        continue
    rel = str(path.relative_to(ROOT))
    if "classes/" in rel or "fixtures/" in rel:
        role = "locally generated Java8 fixture source/class; guest execution only via geth EVM runner"
    elif path.suffix == ".log":
        role = "preserved build/test attempt log"
    elif path.name == "runner":
        role = "compiled local geth EVM runner"
    elif path.name.endswith(".json") and ("Interpreter" in path.name or "Coordinator" in path.name):
        role = "candidate Solidity build artifact"
    else:
        role = "candidate source or pinned evidence"
    data = path.read_bytes()
    files.append({"path": rel, "bytes": len(data), "sha256": sha(data), "role": role})
manifest = {
    "profile": pins["profile"],
    "status": pins["status"],
    "baseCommit": pins["acceptedGuestCodeCommit"],
    "baseSourceManifestSHA256": sha((BASE / "source-manifest.json").read_bytes()),
    "basePinsSHA256": sha((BASE / "pins.json").read_bytes()),
    "compiler": "solc 0.8.30+commit.73712a01; optimizer200 viaIR Cancun metadata hash none",
    "jdk": "OpenJDK 8; javac -source 8 -target 8; no host Java fixture execution",
    "files": files,
}
(ROOT / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"wrote {ROOT / 'source-manifest.json'} with {len(files)} candidate files")
