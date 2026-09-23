#!/usr/bin/env python3
"""Create the P9 candidate from accepted P6 plus only the measured asin delta."""
from pathlib import Path
import re

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
p6_path = root / "evidence/java-evm/minecraft-entry/parent-670d5a8ce/artifacts/engine/MCEntryInterpreter.sol"
asin_path = root / "evidence/java-evm/minecraft-entry/math-asin-bounded-preparation/engine/MCEntryInterpreter.sol"
p6 = p6_path.read_text()
asin = asin_path.read_text()


def function_block(text: str, name: str) -> str:
    start = text.index("    function " + name + "(")
    end = text.find("\n    function ", start + 1)
    return text[start:end if end >= 0 else len(text)]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise AssertionError(f"{label}: expected unique source anchor, got {count}")
    return text.replace(old, new, 1)

source = p6
source = replace_once(
    source,
    "    error MathSinProfileError(uint256 code, uint256 pc);\n",
    "    error MathSinProfileError(uint256 code, uint256 pc);\n"
    "    error MathAsinProfileError(uint256 code, uint256 pc);\n",
    "asin typed refusal",
)
source = replace_once(
    source,
    "    bytes32 private constant DBOOT_MATH = hex\"e354be66a6f5f6eecabb17b461000b63b90bea635f692a0cf0c36b6b5a688748\";",
    "    bytes32 private constant DBOOT_MATH = hex\"109b02106c7d644052ff74938768421a9a78caf8d9bfd2378b943cf567c2d192\";",
    "correct materialized Math leaf",
)
old_math_comment = (
    "            // Binding18 preserves the measured deterministic sqrt surface;\n"
    "            // binding19 is only the measured signed-zero Math.sin leaf. Raw Math\n"
    "            // replacement is refused during preparation.\n"
)
new_math_comment = (
    "            // Binding18 is sqrt, binding19 is bounded integer sin, and binding20\n"
    "            // is the measured bounded integer inverse-sine surface. Raw Math\n"
    "            // replacement remains refused.\n"
)
source = replace_once(source, old_math_comment, new_math_comment, "Math binding comment")
old_sin_map = (
    '            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("sin"))\n'
    '                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(D)D"))) {\n'
    '                return 19;\n'
    '            }\n'
)
source = replace_once(
    source,
    old_sin_map,
    old_sin_map +
    '            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("asin"))\n'
    '                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(D)D"))) {\n'
    '                return 20;\n'
    '            }\n',
    "Math asin binding map",
)
source = replace_once(
    source,
    "                && binding != 18 && binding != 19 && s.argumentKinds.length != 1)",
    "                && binding != 18 && binding != 19 && binding != 20 && s.argumentKinds.length != 1)",
    "binding-20 arity whitelist",
)
source = replace_once(
    source,
    "            || ((binding == 18 || binding == 19) && (s.argumentKinds.length != 1",
    "            || ((binding == 18 || binding == 19 || binding == 20) && (s.argumentKinds.length != 1",
    "binding-20 descriptor validation",
)
old_native_comment = "        // Binding14 is exactly the canonical public instance Throwable native.\n"
new_native_comment = (
    "        // Binding14 is exactly the canonical public instance Throwable native.\n"
)
# Binding20 intentionally uses the default exact public-static-native validation.
assert source.count(old_native_comment) == 1

# Insert the exact global native-20 invocation branch without touching bindings 1..19.
old_dispatch_anchor = "                    if (nativeBinding == 18) {\n"
assert source.count(old_dispatch_anchor) == 1
asin_dispatch = (
    "                    if (nativeBinding == 20) {\n"
    "                        // Consume only the authenticated guest's binary64 bits;\n"
    "                        // the bounded Q120 kernel uses EVM integer operations.\n"
    "                        _requireKind(f.stack[base], KIND_DOUBLE, opPC);\n"
    "                        uint64 raw = uint64(_payload(f.stack[base]));\n"
    "                        f.stack[base] = _packDouble(_mathAsinBits(raw, opPC));\n"
    "                        f.sp = base + 1;\n"
    "                        continue;\n"
    "                    }\n"
)
source = replace_once(source, old_dispatch_anchor, asin_dispatch + old_dispatch_anchor, "binding-20 dispatch")

# Only the three new integer helpers are transferred; nearest-even and binary64
# conversion helpers already exist in P6 and remain byte-identical.
kernel_start = "    /// @dev Bounded Q120 inverse sine over the exact guest binary64 encoding.\n"
kernel_end = "    /// @dev Signed nearest-even integer division; callers prove |numerator| < 2^255.\n"
a = asin.index(kernel_start)
b = asin.index(kernel_end, a)
kernel = asin[a:b]
assert "Math.sin(" not in kernel and "Math.sqrt(" not in kernel
source = replace_once(source, kernel_end, kernel + kernel_end, "Q120 kernel insertion")

# Exact javac --source 8 --target 8 -g:none Math image from the corrected candidate.
new_math = function_block(asin, "_bootstrapMath")
old_math = function_block(p6, "_bootstrapMath")
source = replace_once(source, old_math, new_math, "Math bootstrap image")

# A distinct fresh experiment domain prevents reuse of P6/P8 state or pins.
assert source.count("JVMEVM:MC-RANDOM-CLASS-P6:") == 9
source = source.replace("JVMEVM:MC-RANDOM-CLASS-P6:", "JVMEVM:MC-RANDOM-CLASS-P9:")
(stage / "engine" / "MCEntryInterpreter.sol").write_text(source)
print(f"wrote {stage / 'engine' / 'MCEntryInterpreter.sol'}")
