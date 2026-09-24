#!/usr/bin/env python3
"""TEST-ONLY independent integer Q120 cosine model vs generated Java 8 witnesses."""
from pathlib import Path
import hashlib, json, struct, sys

here = Path(__file__).resolve().parent
root = Path(__file__).resolve().parents[4]
fixtures = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
if fixtures is None:
    candidates = sorted((root / "build").glob("java-diff-mc-integer-rotate-left-fixtures-*"))
    assert candidates, "generate Java8 fixtures first"
    fixtures = candidates[-1]
fixture = json.loads((fixtures / "math-cos-bounded-domain.json").read_text())
assert fixture["java8HostOracle"] is True
Q = 1 << 120
PI_Q = 4175892906503776358826876457663557747
TINY_RAW = 0x3e40000000000000
BOUND_RAW = 0x401921fb54442d18
MASK64 = (1 << 64) - 1
max_bits = {}

def observe(label, value):
    bits = abs(value).bit_length()
    max_bits[label] = max(max_bits.get(label, 0), bits)
    assert abs(value) < (1 << 255), (label, bits)

def even_signed(numerator, denominator, label):
    assert denominator > 0
    negative = numerator < 0
    magnitude = abs(numerator)
    observe(label + ".numerator", magnitude)
    observe(label + ".denominator", denominator)
    quotient, remainder = divmod(magnitude, denominator)
    observe(label + ".twiceRemainder", 2 * remainder)
    if 2 * remainder > denominator or (2 * remainder == denominator and quotient & 1):
        quotient += 1
    observe(label + ".quotient", quotient)
    return -quotient if negative else quotient

def raw_to_q(magnitude):
    exponent = (magnitude >> 52) & 0x7ff
    significand = (1 << 52) | (magnitude & ((1 << 52) - 1))
    value = significand << (exponent - 955)
    observe("inputQ", value)
    return value

def q_to_double(value):
    if value == 0:
        return 0
    negative = value < 0
    magnitude = abs(value)
    top = magnitude.bit_length() - 1
    shift = top - 52
    if shift > 0:
        significand = even_signed(magnitude, 1 << shift, "binary64-round")
    else:
        significand = magnitude << -shift
        observe("binary64-significand", significand)
    if significand == (1 << 53):
        significand >>= 1
        top += 1
    result = ((top + 903) << 52) | (significand & ((1 << 52) - 1))
    return result | ((1 << 63) if negative else 0)

def model(raw):
    magnitude = raw & 0x7fffffffffffffff
    exponent = (magnitude >> 52) & 0x7ff
    if exponent == 0x7ff or magnitude > BOUND_RAW:
        raise ValueError("outside bounded cosine domain")
    if magnitude <= TINY_RAW:
        return 0x3ff0000000000000
    x = raw_to_q(magnitude)
    if x > PI_Q:
        x -= 2 * PI_Q
    observe("reducedX", x)
    x2 = even_signed(x * x, Q, "square")
    term = total = Q
    for n in range(1, 31):
        factor = (2 * n - 1) * (2 * n)
        term = even_signed(-term * x2, Q * factor, "term-%d" % n)
        total += term
        observe("sum-%d" % n, total)
    return q_to_double(total)

def ordered(bits):
    return (~bits & MASK64) if bits >> 63 else bits | (1 << 63)

def as_float_bits(bits):
    value = struct.unpack(">d", struct.pack(">Q", bits))[0]
    return struct.unpack(">I", struct.pack(">f", value))[0]

worst = 0
mismatches = []
float_mismatches = []
for row in fixture["cosVectors"]:
    raw = int(row["inputRaw"], 16)
    got = model(raw)
    expected = int(row["javaDoubleRaw"], 16)
    distance = abs(ordered(got) - ordered(expected))
    worst = max(worst, distance)
    if distance:
        mismatches.append({"name": row["name"], "inputRaw": row["inputRaw"],
                           "modelRaw": "%016x" % got, "java8Raw": "%016x" % expected,
                           "ulpDistance": distance})
    cast = as_float_bits(got)
    want_float = int(row["javaFloatRaw"], 16)
    if cast != want_float:
        float_mismatches.append({"name": row["name"], "modelFloatRaw": "%08x" % cast,
                                 "java8FloatRaw": "%08x" % want_float})
assert worst <= 1, mismatches[:8]
assert not float_mismatches, float_mismatches[:8]
# The unsupported vectors are metadata-only controls; the model never asks a
# host function to calculate a value outside the profile.
refused = ["math-cos-above-bound-refusal", "math-cos-below-negative-bound-refusal",
           "math-cos-nan-refusal", "math-cos-positive-infinity-refusal",
           "math-cos-negative-infinity-refusal"]
for label in refused:
    assert (fixtures / (label + ".zip")).is_file()
report = {
    "purpose": "TEST-ONLY integer Q120 model against separate generated Java8 Math.cos raw results; never guest execution input",
    "fixtureZipSHA256": fixture["zipSHA256"],
    "vectorCount": len(fixture["cosVectors"]),
    "qBits": 120,
    "piQ": str(PI_Q),
    "seriesN": 30,
    "tailBound": "<2^-180 for |x|<=pi",
    "maxBinary64ULPDistanceFromJava8": worst,
    "binary64RawMismatchCount": len(mismatches),
    "floatCastRawMismatchCount": len(float_mismatches),
    "maximumIntermediateBitLengths": dict(sorted(max_bits.items())),
    "strictSigned256Bound": "every observed integer magnitude <2^255",
    "refusalFixtures": refused,
    "samplesSHA256": hashlib.sha256(json.dumps(fixture["cosVectors"], sort_keys=True).encode()).hexdigest(),
    "limitation": "Generated deterministic samples only; no universal Java Math conformance or original-program input is claimed.",
}
# Retain the accepted asin oracle/model controls in the same aggregate report.
import subprocess
asin = json.loads(subprocess.run([sys.executable, here / "verify_asin_q120.py"],
                                 cwd=root, text=True, capture_output=True,
                                 check=True, timeout=120).stdout)
cos_report = dict(report)
report.update({key: asin[key] for key in ("supportedRows", "maxBinary64ULPDistanceFromJava8",
                                         "binary64BitMismatchCount", "floatCastBitMismatchCount",
                                         "refusedControls", "oracleSamplesSHA256")})
report["cosQ120TestOnlyModel"] = cos_report
report["priorAsinQ120TestOnlyModel"] = asin
print(json.dumps(report, indent=2, sort_keys=True))
