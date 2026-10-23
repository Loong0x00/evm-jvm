#!/usr/bin/env python3
"""Synchronize canonical Java 8 class bytes into their Solidity materializers."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
SOL = ROOT / "engine/MCEntryInterpreter.sol"
CLASSES = ROOT / "builds/java8-p2/java/util"
IMAGES = {
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
