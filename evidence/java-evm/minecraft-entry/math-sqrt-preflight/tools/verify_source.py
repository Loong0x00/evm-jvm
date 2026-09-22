#!/usr/bin/env python3
"""Strict source/image derivation for the one-binding Math.sqrt stage.

Only the pinned raw71 parent, this checked-in Java-8 Math declaration, and local
pinned compiler/node modules are read. No original/JAR/resource/network input is
opened or evaluated.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-195ced67d"
assert len(sys.argv) == 3 and sys.argv[1] == "--built"
assert Path(sys.argv[2]).resolve() == stage / "build-pins.json"

DOMAIN = "MC-MATH-SQRT-P1"
PARENT_DOMAIN = "MC-SYSTEM-IDENTITY-HASH-P3"
MATH_SHA256 = "6092139a4281d1a0cbbaf5292ad894a4d494f5589a45605081ccb12ac3ed9861"
MATH_KECCAK = "2d564544678da031e6acf47de0b92aceaeb777cc8829613397b3669ed4aeb478"
ROOT = "8e1744b2bd9a32e654e5e043b24d64e1da828395099a6a6b6281a025457f93ec"
ENGINE = {"bytes": 382816, "initSHA256": "fd075d2f3cc7eed897b8fb2bad8a5cb4cdb4edcfaa615d1b11fafc06da329357", "runtimeSHA256": "ca1af2ecd4f49e36c20b40b2233de358fde263ef3e30a578e2ec4cf9e2cd3b76", "runtimeKeccak256": "9ae8a2e5e920c5ecb09816929a47406cc61caa6cd2436196378dc4f38834d765"}
COORDINATOR = {"bytes": 5386, "initSHA256": "1f705323ac9e08b39fde8a6b9989bf09d1968568694d5fe4baca4de1230c90bb", "runtimeSHA256": "619248ca47c07d8e88bf012f5239076b818247a25b37b194550a193309b530c0", "runtimeKeccak256": "27ed20fd3dd8a1ebbec37007c7b55f848e9f5a14d23e8538339692873b90e4ff"}
ADDRESS = "0x4d432d4d4154482d535152542d50310000000000"
OWNER = "0x4d432d4d4154482d535152542d50310000000001"
PARENT_FILES = {
    "pins.json": "b7d4e40efabc927e6fbb184f8acaec176fe165d7ead223f5460a568b6294fb39",
    "artifacts/engine/MCEntryInterpreter.sol": "ab4c53cbd42dea8175c1a41cf1b25ac439e2972a9121daa98a9baa50f08ed152",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/MCEntryCoordinator.sol": "60f8b6f977c9b1c14a378e7aa97255fe47e3e6e6fd8cdf6ff1f4473dca7849fb",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "canonical-driver.go.txt": "26db5594aacbfff74fff875c88724a5e656898c03afc662c6621d39c61c1702a",
    "checkpoint_diagnostic.py": "b574d12eae393f570e37be0f15cc4f7ebe92566afd0df1cda8f3125bd0881515",
    "checkpoint_frames.py": "77f54826765d468abd6ace23d9bf63a93afba9780baf27346494b744d89ccb70",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:96], text.count(old), count)
    return text.replace(old, new)


def image(text, function):
    start = text.index("function " + function + "(")
    end = text.find("\n    function ", start + 1)
    values = re.findall(r'hex"([0-9a-f]+)"', text[start:end if end >= 0 else len(text)])
    assert len(values) == 1, (function, len(values))
    return bytes.fromhex(values[0])


def expected_engine(parent_engine, math_hex):
    text = exact(parent_engine, PARENT_DOMAIN, DOMAIN, 9)
    old_math = image(text, "_bootstrapMath").hex()
    text = exact(text, old_math, math_hex)
    text = exact(text, 'bytes32 private constant DBOOT_MATH = hex"dbb6f1d4402cef41ec516276bf659206c1c62c913983f7de441e5c3dab998931";',
                 'bytes32 private constant DBOOT_MATH = hex"%s";' % MATH_KECCAK)
    old = '''        } else if (_isNamedClass(c, bytes("java/lang/Double"))) {
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("longBitsToDouble"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(J)D"))) {
                return 3;
            }
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("doubleToRawLongBits"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(D)J"))) {
                return 4;
            }
        } else if (_isNamedClass(c, bytes("java/lang/System"))) {'''
    new = old[:-len('        } else if (_isNamedClass(c, bytes("java/lang/System"))) {')] + '''        } else if (_isNamedClass(c, bytes("java/lang/Math"))) {
            // Binding18 is the sole Math floating surface. Raw Math replacement
            // is refused at preparation, and only this exact native declaration
            // can reach the deterministic uint256 binary64 square-root kernel.
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("sqrt"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(D)D"))) {
                return 18;
            }
        } else if (_isNamedClass(c, bytes("java/lang/System"))) {'''
    text = exact(text, old, new)
    text = exact(text, '''                && binding != 14 && binding != 15 && binding != 16 && binding != 17
                && s.argumentKinds.length != 1)''', '''                && binding != 14 && binding != 15 && binding != 16 && binding != 17
                && binding != 18 && s.argumentKinds.length != 1)''')
    text = exact(text, '''            || (binding == 17 && (s.argumentKinds.length != 1
                || s.argumentKinds[0] != KIND_REF || s.returnKind != 1
                || s.returnSubtype != uint8(bytes1("I"))
                || !_equalsLiteral(c.data, s.argumentTypeOffsets[0], s.argumentTypeLengths[0],
                    bytes("Ljava/lang/Object;"))))) {''', '''            || (binding == 17 && (s.argumentKinds.length != 1
                || s.argumentKinds[0] != KIND_REF || s.returnKind != 1
                || s.returnSubtype != uint8(bytes1("I"))
                || !_equalsLiteral(c.data, s.argumentTypeOffsets[0], s.argumentTypeLengths[0],
                    bytes("Ljava/lang/Object;"))))
            || (binding == 18 && (s.argumentKinds.length != 1
                || s.argumentWords != 2 || s.argumentKinds[0] != KIND_DOUBLE
                || s.returnKind != 6
                || !_equalsLiteral(c.data, s.descriptorOffset, s.descriptorLength,
                    bytes("(D)D"))))) {''')
    old = '''                    if (nativeBinding == 17) {
                        // Argument shape/assignability was checked above. Validate the
                        // exact packed guest reference again before exposing its stable
                        // low uint32 handle; zero maps to Java's required zero result.
                        // This reads only the existing heap frontier: no host identity,
                        // hashCode dispatch, allocation, initialization or mutation.
                        _validatePackedRef(f.stack[base], heapKinds, nextHandle, opPC);
                        f.stack[base] = _packInt(uint32(_payload(f.stack[base])));
                        f.sp = base + 1;
                        continue;
                    }
                    if (nativeBinding == 6) {'''
    new = old.replace('''                    if (nativeBinding == 6) {''', '''                    if (nativeBinding == 18) {
                        // The selected exact (D)D signature requires a category-2
                        // double value and records its two JVM words before this
                        // compact stack representation reaches native dispatch.
                        _requireKind(f.stack[base], KIND_DOUBLE, opPC);
                        f.stack[base] = _packDouble(_mathSqrtBits(uint64(_payload(f.stack[base]))));
                        f.sp = base + 1;
                        continue;
                    }
                    if (nativeBinding == 6) {''')
    text = exact(text, old, new)
    marker = '''    function _compareIEEE(
        uint64 left, uint64 right, uint256 exponentBits, uint256 fractionBits, bool nanLow
    ) private pure returns (int8) {'''
    helper = '''    /// @dev Deterministic IEEE-754 binary64 sqrt over guest raw bits only.
    /// Finite positive inputs are normalized into M*2^scale with M in [2^52,2^53).
    /// Making scale even gives a <=106-bit radicand M<<52 (or M<<53); a fixed
    /// 53-round restoring square root supplies its floor and exact remainder.
    /// The four-times midpoint comparison implements round-to-nearest-even
    /// without EVM/host floating point, precompiles, or guest-controlled loops.
    function _mathSqrtBits(uint64 raw) private pure returns (uint64) {
        uint256 magnitude = uint256(raw) & 0x7fffffffffffffff;
        // Preserve both Java zero encodings before interpreting a sign bit.
        if (magnitude == 0) return raw;
        uint256 exponent = (uint256(raw) >> 52) & 0x7ff;
        uint256 fraction = uint256(raw) & 0x000fffffffffffff;
        // Java permits a quiet NaN result for every NaN input. Positive infinity
        // is fixed; negative infinity and every negative finite input are NaN.
        if (exponent == 0x7ff) {
            if (fraction == 0 && (uint256(raw) >> 63) == 0) return raw;
            return 0x7ff8000000000000;
        }
        if ((uint256(raw) >> 63) != 0) return 0x7ff8000000000000;

        uint256 significand;
        int256 scale;
        if (exponent == 0) {
            // The nonzero subnormal is brought to the same 53-bit interval as a
            // normal. This is deliberately a fixed 52-round scan, not a loop
            // whose termination depends on a guest exponent or magnitude.
            uint256 probe = fraction;
            uint256 top;
            unchecked {
                for (uint256 i; i < 52; ++i) {
                    if (probe > 1) {
                        probe >>= 1;
                        ++top;
                    }
                }
            }
            uint256 shift = 52 - top;
            significand = fraction << shift;
            scale = -1074 - int256(shift);
        } else {
            significand = (uint256(1) << 52) | fraction;
            scale = int256(exponent) - 1075;
        }
        uint256 radicand = significand;
        int256 halfScale;
        if (scale % 2 != 0) {
            radicand <<= 1;
            halfScale = (scale - 1) / 2;
        } else {
            halfScale = scale / 2;
        }
        (uint256 root, uint256 remainder) = _integerSqrt106(radicand << 52);
        // Compare sqrt(N) to root + 1/2 exactly: 4N ? (2root+1)^2.
        // Equality cannot occur for integral N (right side is 1 mod 4), but
        // retain the even tie rule explicitly as the IEEE rounding contract.
        uint256 left = remainder << 2;
        uint256 midpoint = (root << 2) | 1;
        if (left > midpoint || (left == midpoint && (root & 1) != 0)) ++root;
        int256 encodedExponent = halfScale + 1049;
        // A rounded 2^53 significand is renormalized exactly into the next binade.
        if (root == (uint256(1) << 53)) {
            root = uint256(1) << 52;
            ++encodedExponent;
        }
        return uint64((uint256(encodedExponent) << 52) | (root & 0x000fffffffffffff));
    }

    /// @dev Fixed restoring integer sqrt for a radicand below 2^106.
    /// Exactly 53 iterations consume the powers of four 2^104 through 2^0.
    function _integerSqrt106(uint256 value) private pure returns (uint256 root, uint256 remainder) {
        uint256 bit = uint256(1) << 104;
        remainder = value;
        unchecked {
            for (uint256 i; i < 53; ++i) {
                uint256 trial = root + bit;
                if (remainder >= trial) {
                    remainder -= trial;
                    root = (root >> 1) + bit;
                } else {
                    root >>= 1;
                }
                bit >>= 2;
            }
        }
    }

'''
    return exact(text, marker, helper + marker)


def root_leaves(text):
    body = text[text.index("function _bootstrapRoot"):text.index("function _prepare")]
    assignments = re.findall(r'h\[(\d+)\] = (?:keccak256\()?(?:(_[A-Za-z0-9]+)\(\)|(DBOOT_[A-Z_]+))(?:\))?;', body)
    assert len(assignments) == 96 and [int(x[0]) for x in assignments] == list(range(96))
    result = []
    for _, function, constant in assignments:
        if function: result.append({"image": image(text, function).hex()})
        else:
            at = text.index("bytes32 private constant " + constant)
            declaration = text[at:text.index(";", at)]
            folded = re.search(r'keccak256\(hex"([0-9a-f]+)"\)', declaration)
            literal = re.search(r'= hex"([0-9a-f]+)"', declaration)
            assert folded or literal, constant
            result.append({"image": folded.group(1)} if folded else {"hash": literal.group(1)})
    return result


def class_methods(data):
    def u2(at): return int.from_bytes(data[at:at + 2], "big"), at + 2
    def u4(at): return int.from_bytes(data[at:at + 4], "big"), at + 4
    assert data[:8] == bytes.fromhex("cafebabe00000034")
    at = 8; count, at = u2(at); cp = [None] * count; index = 1
    while index < count:
        tag = data[at]; at += 1
        if tag == 1: n, at = u2(at); cp[index] = (tag, data[at:at+n]); at += n
        elif tag in (3, 4): at += 4
        elif tag in (5, 6): at += 8; index += 1
        elif tag in (7, 8, 16, 19, 20): value, at = u2(at); cp[index] = (tag, value)
        elif tag in (9, 10, 11, 12, 18): at += 4
        elif tag == 15: at += 3
        else: raise AssertionError(("cp", tag))
        index += 1
    def utf(i): assert cp[i][0] == 1; return cp[i][1]
    access, at = u2(at); _, at = u2(at); _, at = u2(at); interfaces, at = u2(at); at += 2 * interfaces
    def members():
        nonlocal at
        amount, at = u2(at); rows = []
        for _ in range(amount):
            flags, at = u2(at); name, at = u2(at); descriptor, at = u2(at); attrs, at = u2(at)
            for _ in range(attrs): _, at = u2(at); n, at = u4(at); at += n
            rows.append((flags, utf(name), utf(descriptor)))
        return rows
    fields = members(); methods = members(); attrs, at = u2(at)
    for _ in range(attrs): _, at = u2(at); n, at = u4(at); at += n
    assert at == len(data)
    return access, fields, methods


assert {name: sha(parent / name) for name in PARENT_FILES} == PARENT_FILES
parent_pins = json.loads((parent / "pins.json").read_text())
pins = json.loads((stage / "build-pins.json").read_text())
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({"basis": "parent-195ced67d", "parentEvidence": "parent-195ced67d/artifacts/{engine,coordinator}+canonical-driver+pins", "domain": DOMAIN, "bootstrapRoot": ROOT, "globalNativeBindings": 18, "address": ADDRESS, "owner": OWNER, "engine": ENGINE, "coordinator": COORDINATOR, "worker": "math-sqrt"})
expected_pins["bootstrapSHA256"] = dict(parent_pins["bootstrapSHA256"])
expected_pins["bootstrapSHA256"]["Math"] = MATH_SHA256
expected_pins["math"] = {"slot": 89, "bytes": 275, "sha256": MATH_SHA256, "keccak256": MATH_KECCAK, "surface": "private constructor, retained int min/max, and exact native sqrt(double) only", "java8": "javac -source 8 -target 8 -g:none"}
assert pins == expected_pins
assert pins["rawLimits"] == [71, 471911] and pins["bootstrapCount"] == 96 and pins["diagnosticClassBound"] == 167
assert pins["stringLocalBinding"] == 12 and pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216

source = (stage / "bootstrap/java/lang/Math.java").read_text()
assert source == '''package java.lang;

/** Bounded Java 8 Math surface: int min/max and deterministic native binary64 sqrt only. */
public final class Math {
    private Math() {}

    public static int max(int a, int b) { if (a >= b) return a; return b; }
    public static int min(int a, int b) { if (a <= b) return a; return b; }

    public static native double sqrt(double value);
}
'''
for forbidden in ("StrictMath", "cbrt", "random", "doubleToLongBits", "host", "Math."):
    assert forbidden not in source, forbidden
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac"); assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="math-sqrt-verify-", dir=root / "build") as name:
    temp = Path(name); src = temp / "java/lang/Math.java"; src.parent.mkdir(parents=True); src.write_text(source); output = temp / "out"; output.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", output, src], check=True)
    math = (output / "java/lang/Math.class").read_bytes()
assert len(math) == 275 and hashlib.sha256(math).hexdigest() == MATH_SHA256
assert math.hex() == "".join((stage / "bootstrap/java/lang/Math.class.hex").read_text().split())
assert (stage / "bootstrap/java/lang/Math.sha256").read_text().split()[0] == MATH_SHA256
access, fields, methods = class_methods(math)
assert access == 0x31 and fields == []
assert methods == [(0x0002, b"<init>", b"()V"), (0x0009, b"max", b"(II)I"), (0x0009, b"min", b"(II)I"), (0x0109, b"sqrt", b"(D)D")]

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == expected_engine(parent_engine, math.hex())
for fixed in ("MAX_RAW_CLASSES = 71;", "MAX_RAW_BYTES = 471911;", "MAX_CHECKPOINT_BYTES = 1048576;", "MAX_FRAMES = 128;", "new bytes32[](96)", "new uint256[](14)", "return 18;", "s.argumentWords != 2", "KIND_DOUBLE", "for (uint256 i; i < 52; ++i)", "for (uint256 i; i < 53; ++i)"):
    assert engine.count(fixed) >= 1, fixed
assert engine.count("return 18;") == engine.count("nativeBinding == 18") == engine.count("binding == 18") == 1
assert engine.count("binding != 18") == 1 and engine.count("_mathSqrtBits(") == 2 and engine.count("_integerSqrt106(") == 2
sqrt_body = engine[engine.index("function _mathSqrtBits"):engine.index("function _compareIEEE")]
assert "while" not in sqrt_body and "_highestBit(" not in sqrt_body
for forbidden in ("staticcall", "delegatecall", ".call", "precompile", "block.", "tx.", "abi.decode"):
    assert forbidden not in sqrt_body, forbidden
assert hashlib.sha256(image(engine, "_bootstrapMath")).hexdigest() == MATH_SHA256
for name, function in (("System", "_bootstrapSystem"), ("String", "_bootstrapString"), ("Locale", "_bootstrapLocale"), ("MapEntry", "_bootstrapMapEntry"), ("Integer", "_bootstrapInteger")):
    assert hashlib.sha256(image(engine, function)).hexdigest() == pins["bootstrapSHA256"].get(name, pins[name.lower()]["sha256"] if name.lower() in pins else None), name

parent_leaves, leaves = root_leaves(parent_engine), root_leaves(engine)
assert len(parent_leaves) == len(leaves) == 96
assert [i for i, (old, new) in enumerate(zip(parent_leaves, leaves)) if old != new] == [89]
assert leaves[89] == {"hash": MATH_KECCAK}
record = json.loads((stage / "root-commitment.json").read_text())
assert record["bootstrapCount"] == 96 and record["bootstrapRoot"] == ROOT and record["changedLeafSlots"] == [89] and record["mathLeafKeccak256"] == MATH_KECCAK
node_modules = root / "jvmevm/runtime/node_modules"; assert node_modules.is_dir()
node = 'const{keccak256}=require("js-sha3");const p=JSON.parse(process.argv[1]),w=x=>x.padStart(64,"0"),h=p.l.map(x=>x.image?keccak256(Buffer.from(x.image,"hex")):x.hash),r=keccak256(Buffer.from(w(p.d)+w("40")+w(h.length.toString(16))+h.map(w).join(""),"hex"));console.log(JSON.stringify({leaves:h,root:r}));'
dboot = re.search(r'bytes32 private constant DBOOT = keccak256\("([^"]+)"\)', engine).group(1).encode().hex()
folded = json.loads(subprocess.check_output(["node", "-e", node, json.dumps({"d": dboot, "l": leaves})], cwd=root, env={**os.environ, "NODE_PATH": str(node_modules)}, text=True))
assert folded["root"] == ROOT and folded["leaves"] == record["leafKeccak256"]

parent_coord = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coord = exact(parent_coord, PARENT_DOMAIN, DOMAIN, 4)
coord = exact(coord, "4d432d53595354454d2d4944454e54495459313b", ADDRESS[2:])
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == coord
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()

# The driver has no semantic delta beyond its fixed product identities/domains.
driver = (parent / "canonical-driver.go.txt").read_text()
driver = exact(driver, PARENT_DOMAIN, DOMAIN, 6)
for old, new in ((parent_pins["address"], ADDRESS), (parent_pins["owner"], OWNER), (parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"]), ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"]), ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])):
    driver = exact(driver, old, new)
for name, value in (("engineRun", ENGINE["bytes"]), ("coordRun", COORDINATOR["bytes"]), ("run", ENGINE["bytes"])):
    driver, changed = re.subn(r"(len\(" + name + r"\) != )\d+", r"\g<1>" + str(value), driver)
    assert changed == 1, name
assert (stage / "tools/Go.txt").read_text() == driver
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py", "verify_receipts.js"):
    assert (stage / "tools" / name).read_bytes() == (parent / name).read_bytes(), name

print(json.dumps({"basis": "parent-195ced67d", "domain": DOMAIN, "math": {"bytes": len(math), "sha256": MATH_SHA256, "keccak256": MATH_KECCAK}, "bootstrapRoot": ROOT, "changedBootstrapLeaves": [89], "rawLimits": [71, 471911], "globalNativeBindings": 18, "stringLocalBinding": 12, "engine": ENGINE, "coordinator": COORDINATOR, "verification": "exact-one-Math-image+binding18+fixed-uint256-sqrt+independent-ordered-root"}, indent=2))
