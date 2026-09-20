#!/usr/bin/env python3
"""Emit the exact compact Java-8 PrintStream bootstrap image.

The balanced monitor pair is intentional: it performs the guest null check
before recording the exact String reference, without javac handler scaffolding.
It reads no external class, JAR, resource, or host output.
"""
from pathlib import Path
IMAGE = bytes.fromhex("cafebabe00000034000f0a0004000b090003000c07000d07000e0100124c6a6176612f6c616e672f537472696e673b0100063c696e69743e010003282956010004436f64650100077072696e746c6e010015284c6a6176612f6c616e672f537472696e673b29560c000600070c000900050100136a6176612f696f2f5072696e7453747265616d0100106a6176612f6c616e672f4f626a6563740021000300040000000100020009000500000002000100060007000100080000001100010001000000052ab70001b10000000000010009000a0001000800000016000200020000000a2bc22bc32a2bb50002b1000000000000" )
def build() -> bytes: return IMAGE
if __name__ == "__main__": (Path(__file__).parent / "java/io/PrintStream.class.hex").write_text(IMAGE.hex() + "\n")
