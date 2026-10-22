#!/usr/bin/env python3
"""Generate the P38 engine source from the pinned P37 source-only baseline."""
from __future__ import annotations
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
ROOT = STAGE.parents[3]
BASE = ROOT / "evidence/java-evm/minecraft-entry/string-replaceall-source-base-p37"
CANDIDATE = STAGE / "reference/string-replaceall-bounded/engine/MCEntryInterpreter.sol"


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise AssertionError(f"expected one source anchor, got {count}: {old[:120]!r}")
    return text.replace(old, new, 1)


def materializer(name: str, image: bytes) -> str:
    return (f'    function _bootstrap{name}() private pure returns (bytes memory) '
            f'{{ return hex"{image.hex()}"; }}')


def function_span(source: str, name: str) -> tuple[int, int]:
    start = source.index(f"    function _bootstrap{name}(")
    end = source.find("\n    function ", start + 1)
    if end < 0:
        end = source.rfind("\n}")
    return start, end


def main() -> None:
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: generate_engine_source.py JAVA8_CLASSES_DIR [OUTPUT_SOL]")
    classes = Path(sys.argv[1]).resolve()
    destination = Path(sys.argv[2]).resolve() if len(sys.argv) == 3 else CANDIDATE
    images = {
        name: (classes / package / f"{name}.class").read_bytes()
        for name, package in (
            ("String", "java/lang"),
            ("Pattern", "java/util/regex"),
            ("Matcher", "java/util/regex"),
        )
    }
    base = (BASE / "engine/MCEntryInterpreter.sol").read_text()
    source = base.replace("MC-ARRAY-CLONE-INTRINSIC-P37", "MC-STRING-REPLACEALL-BOUNDED-P38")
    assert source != base
    source = replace_once(source, "bytes32[] memory h = new bytes32[](103);",
                          "bytes32[] memory h = new bytes32[](104);")
    source = replace_once(
        source,
        "        h[102] = keccak256(_bootstrapPatternSyntaxException());\n        return keccak256(abi.encode(DBOOT, h));",
        "        h[102] = keccak256(_bootstrapPatternSyntaxException());\n"
        "        // Minimal bounded Matcher appends after the unchanged P37 tail.\n"
        "        h[103] = keccak256(_bootstrapMatcher());\n"
        "        return keccak256(abi.encode(DBOOT, h));",
    )
    source = replace_once(source, "uint256 count = inputCount + 97 + (suppliedObject ? 0 : 1)",
                          "uint256 count = inputCount + 98 + (suppliedObject ? 0 : 1)")
    source = replace_once(
        source,
        "        p.classes[classSlot + 63].data = _bootstrapPatternSyntaxException();",
        "        p.classes[classSlot + 63].data = _bootstrapPatternSyntaxException();\n"
        "        // Matcher is the only new image and appends after all 103 P37 images.\n"
        "        p.classes[classSlot + 64].data = _bootstrapMatcher();",
    )
    source = replace_once(
        source,
        "        return _isNamedClass(c, bytes(\"java/util/regex/Pattern\"))\n"
        "            || _isNamedClass(c, bytes(\"java/util/regex/PatternSyntaxException\"));",
        "        return _isNamedClass(c, bytes(\"java/util/regex/Pattern\"))\n"
        "            || _isNamedClass(c, bytes(\"java/util/regex/PatternSyntaxException\"))\n"
        "            || _isNamedClass(c, bytes(\"java/util/regex/Matcher\"));",
    )
    for name in ("String", "Pattern"):
        start, end = function_span(source, name)
        source = source[:start] + materializer(name, images[name]) + source[end:]
    # PSE is retained byte-for-byte and the new image is appended after it.
    close = "\n}"
    source = source.rstrip("\n")
    if not source.endswith(close):
        raise AssertionError("unexpected P37 engine file terminator")
    source = source[:-len(close)] + "\n\n"
    source += "    /// @dev Minimal Java 8 Matcher image for the bounded replaceAll profile.\n"
    source += materializer("Matcher", images["Matcher"]) + "\n}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source)
    print(f"wrote {destination} ({len(source.encode())} bytes)")


if __name__ == "__main__":
    main()
