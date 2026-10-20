#!/usr/bin/env python3
"""TEST-ONLY exact-integer Q120 model checked against pinned Java 8 oracle data."""
from pathlib import Path
import hashlib
import json
import struct
import sys

here = Path(__file__).resolve().parent
root = here.parents[3]
oracle = root / "evidence/java-evm/minecraft-entry/math-sin-independent-oracle"
sample_path = oracle / "results/samples.tsv"
assert hashlib.sha256(sample_path.read_bytes()).hexdigest() == "6001a5c714608ca9649b08b25eba27a3aa011f7c870a32ddae15ca330fefc058"
Q = 1 << 120
PI_Q = 4175892906503776358826876457663557747
TWO_PI_Q = 2 * PI_Q
MAX_RAW = 0x401921FB54442D18
SMALL_RAW = 0x3E30000000000000
MASK64 = (1 << 64) - 1


def round_even(n, d):
    assert d > 0
    sign = -1 if n < 0 else 1
    q, r = divmod(abs(n), d)
    if 2 * r > d or (2 * r == d and q & 1):
        q += 1
    return sign * q


def q_to_binary64(value):
    if value == 0:
        return 0
    sign = value < 0
    mag = abs(value)
    top = mag.bit_length() - 1
    if top < 52:
        significand = mag << (52 - top)
    else:
        shift = top - 52
        significand = mag >> shift
        if shift:
            rem = mag & ((1 << shift) - 1)
            half = 1 << (shift - 1)
            if rem > half or (rem == half and significand & 1):
                significand += 1
        if significand == 1 << 53:
            significand >>= 1
            top += 1
    return ((int(sign) << 63) | ((top + 903) << 52) |
            (significand & ((1 << 52) - 1)))


def sin_bits(raw):
    mag = raw & 0x7FFFFFFFFFFFFFFF
    exponent = (mag >> 52) & 0x7FF
    if exponent == 0x7FF or mag > MAX_RAW:
        raise ValueError("outside bounded profile")
    if mag == 0 or mag <= SMALL_RAW:
        return raw
    # For this branch exponent is 995..1025; the exact guest binary64 value
    # multiplied by 2^120 is significand << (exponent-955).
    assert 995 <= exponent <= 1025
    significand = (1 << 52) | (mag & ((1 << 52) - 1))
    x = significand << (exponent - 955)
    if raw >> 63:
        x = -x
    if x > PI_Q:
        x -= TWO_PI_Q
    elif x < -PI_Q:
        x += TWO_PI_Q
    x2 = round_even(x * x, Q)
    term = total = x
    max_product = x * x
    max_term_product = 0
    for n in range(1, 31):
        product = -term * x2
        max_term_product = max(max_term_product, abs(product))
        term = round_even(product, Q * (2 * n) * (2 * n + 1))
        total += term
    assert abs(x) < 1 << 122
    assert abs(x2) < 1 << 124
    assert max_product < 1 << 244
    assert max_term_product < 1 << 246
    assert abs(total) < 1 << 127
    return q_to_binary64(total) | (raw & (1 << 63) if total == 0 else 0)


def ordered(bits):
    return (~bits & MASK64) if bits >> 63 else bits | (1 << 63)


def float_bits_from_double(bits):
    value = struct.unpack(">d", struct.pack(">Q", bits))[0]
    return struct.unpack(">I", struct.pack(">f", value))[0]


grid_rows = []
edge_rows = []
with sample_path.open("r", encoding="ascii", newline="") as stream:
    assert stream.readline().rstrip("\n") == "kind\tkey\tx_raw_bits\tmath_sin_raw_bits\tfloat_cast_raw_bits"
    for line in stream:
        fields = line.rstrip("\n").split("\t")
        assert len(fields) == 5
        row = (fields[0], fields[1], int(fields[2], 16), int(fields[3], 16), int(fields[4], 16))
        (grid_rows if row[0] == "GRID" else edge_rows).append(row)
assert len(grid_rows) == 65536 and len(edge_rows) == 23

double_mismatches = []
float_mismatches = []
max_ulp = 0
for kind, key, raw, java_double, java_float in grid_rows:
    got = sin_bits(raw)
    distance = abs(ordered(got) - ordered(java_double))
    max_ulp = max(max_ulp, distance)
    if got != java_double:
        double_mismatches.append((int(key), got, java_double))
    if float_bits_from_double(got) != java_float:
        float_mismatches.append((int(key), float_bits_from_double(got), java_float))
assert max_ulp <= 1
assert len(double_mismatches) == 2008 and len(float_mismatches) == 0

edge_checked = []
for kind, key, raw, java_double, java_float in edge_rows:
    mag = raw & 0x7FFFFFFFFFFFFFFF
    if ((mag >> 52) & 0x7FF) == 0x7FF or mag > MAX_RAW:
        continue
    got = sin_bits(raw)
    dist = abs(ordered(got) - ordered(java_double))
    assert dist <= 1, (key, hex(got), hex(java_double), dist)
    assert float_bits_from_double(got) == java_float, (key, hex(got), hex(java_float))
    edge_checked.append(key)

records = "".join("%d\t%016x\t%016x\n" % row for row in double_mismatches).encode("ascii")
report = {
    "purpose": "test-only exact integer model; no execution-path authority",
    "oracleSHA256": hashlib.sha256(sample_path.read_bytes()).hexdigest(),
    "gridInputs": len(grid_rows), "boundedFiniteEdgeInputsChecked": len(edge_checked),
    "qBits": 120, "piQ": str(PI_Q), "fixedTaylorUpdates": 30,
    "maxBinary64ULPDistanceFromJava8": max_ulp,
    "binary64BitMismatchCount": len(double_mismatches),
    "binary64MismatchRecordsSHA256": hashlib.sha256(records).hexdigest(),
    "floatCastBitMismatchCount": len(float_mismatches),
    "analyticalStrictProductBound": "<2^246",
    "analyticalStrictAccumulatorBound": "<2^127",
    "bounds": {"absXQ": "<2^122", "absX2": "<2^124", "product": "<2^246",
               "absAccumulator": "<2^127", "signedLimit": "2^255"},
    "warning": "Java8 agreement is measured only on these generated inputs, not a universal correctly-rounded guarantee.",
}
print(json.dumps(report, indent=2, sort_keys=True))
