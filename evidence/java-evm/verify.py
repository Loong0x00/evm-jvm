"""Verify exact archived parent evidence; run from any working directory."""
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
repo = here.parent.parent
manifest = json.loads((here / "manifest.json").read_text())
seen = set()
for item in manifest["files"]:
    path = (repo / item["path"]).resolve()
    if not path.is_relative_to(here) or path in seen:
        raise SystemExit("invalid or duplicate archive path: " + item["path"])
    seen.add(path)
    raw = path.read_bytes()
    if len(raw) != item["bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
        raise SystemExit("archive integrity mismatch: " + item["path"])
print(f"Verified {len(seen)} archived evidence files")
