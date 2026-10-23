#!/usr/bin/env python3
"""Synchronize canonical Java 8 class bytes into their Solidity materializers."""
from pathlib import Path
import re, subprocess, sys

ROOT = Path(__file__).resolve().parent
SOL = ROOT / "engine/MCEntryInterpreter.sol"
OUT = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT / "builds/java8-parent-corrected"
if OUT.exists(): raise SystemExit("choose a new Java image output directory; previous attempts are preserved")
OUT.mkdir(parents=True)
JAVAC = "/usr/lib/jvm/java-8-openjdk/bin/javac"
common = [JAVAC,"-g:none","-source","8","-target","8","-d",str(OUT)]
subprocess.run(common+[str(ROOT/"bootstrap/java/util/HashMap.java"),str(ROOT/"bootstrap/java/util/ConcurrentModificationException.java")],check=True)
# Map$Entry is compile-time source context only. Do not materialize it: its
# independently accepted bootstrap image remains pinned byte-for-byte.
subprocess.run(common+[str(ROOT/"bootstrap/java/util/Map.java")],check=True)
CLASSES = OUT / "java/util"
IMAGES = {
    "_bootstrapMap": "Map.class",
    "_bootstrapHashMap": "HashMap.class",
    "_bootstrapHashMapNode": "HashMap$Node.class",
    "_bootstrapHashMapEntrySet": "HashMap$EntrySet.class",
    "_bootstrapHashMapEntryIterator": "HashMap$EntryIterator.class",
    "_bootstrapConcurrentModificationException": "ConcurrentModificationException.class",
}
source = SOL.read_text()
for method, class_name in IMAGES.items():
    raw = (CLASSES / class_name).read_bytes().hex()
    pattern = rf'(function {method}\(\) private pure returns \(bytes memory\) \{{ return hex")[0-9a-f]+("; \}})'
    source, count = re.subn(pattern, lambda m: m.group(1) + raw + m.group(2), source, count=1)
    if count != 1:
        raise SystemExit(f"expected exactly one Solidity materializer for {method}")
SOL.write_text(source)
print("synchronized Java 8 class bytes:", ", ".join(IMAGES))
