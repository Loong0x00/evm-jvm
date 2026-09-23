#!/usr/bin/env python3
"""TEST-ONLY Q120 integer-Taylor comparison against the Java 8 fixture."""
import decimal
import fractions
import hashlib
import json
import struct
import sys

Q_BITS = 120
Q = 1 << Q_BITS
PI_DECIMAL = (
    "3.14159265358979323846264338327950288419716939937510582097494459230781640628620899862803482534211706798214808651328230664709384460955058223172535940812848111745028410270193852110555964462294895493038196"
)


def round_div_even(numerator, denominator):
    """Exact signed integer division rounded to nearest, ties to even."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    sign = -1 if numerator < 0 else 1
    quotient, remainder = divmod(abs(numerator), denominator)
    twice = 2 * remainder
    if twice > denominator or (twice == denominator and quotient & 1):
        quotient += 1
    return sign * quotient


def q120_pi():
    with decimal.localcontext() as context:
        context.prec = 220
        scaled = decimal.Decimal(PI_DECIMAL) * decimal.Decimal(Q)
        return int(scaled.to_integral_value(rounding=decimal.ROUND_HALF_EVEN))


def float_from_bits(bits):
    return struct.unpack(">d", struct.pack(">Q", bits))[0]


def raw_double_bits(value):
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def raw_float_bits(value):
    return struct.unpack(">I", struct.pack(">f", value))[0]


def sin_q120(x, pi_q):
    exact_x = fractions.Fraction.from_float(x)
    xq = round_div_even(exact_x.numerator * Q, exact_x.denominator)
    if xq > pi_q:
        xq -= 2 * pi_q
    elif xq < -pi_q:
        xq += 2 * pi_q

    term = xq
    total = xq
    for n in range(1, 31):
        denominator = Q * Q * (2 * n) * (2 * n + 1)
        term = round_div_even(-term * xq * xq, denominator)
        total += term
    # Fraction-to-float uses exact integer numerator/denominator conversion;
    # there is no host sin/cos, libm, float-precision polynomial, or EVM path.
    return float(fractions.Fraction(total, Q))


def main(path):
    pi_q = q120_pi()
    mismatch_double = []
    mismatch_float = []
    count = 0
    previous_index = -1
    with open(path, "r", encoding="ascii", newline="") as fixture:
        header = fixture.readline().rstrip("\n")
        if header != "kind\tkey\tx_raw_bits\tmath_sin_raw_bits\tfloat_cast_raw_bits":
            raise SystemExit("unexpected fixture header")
        for line in fixture:
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 5 or fields[0] != "GRID":
                continue
            index = int(fields[1])
            if index != previous_index + 1:
                raise SystemExit("non-contiguous grid index at %d" % index)
            previous_index = index
            x = float_from_bits(int(fields[2], 16))
            java_double = int(fields[3], 16)
            java_float = int(fields[4], 16)
            reference = sin_q120(x, pi_q)
            reference_double = raw_double_bits(reference)
            reference_float = raw_float_bits(reference)
            count += 1
            if reference_double != java_double:
                mismatch_double.append((index, reference_double, java_double))
            if reference_float != java_float:
                mismatch_float.append((index, reference_float, java_float))

    if count != 65536 or previous_index != 65535:
        raise SystemExit("expected 65536 contiguous GRID rows; got %d" % count)

    def mismatch_digest(rows):
        text = "".join("%d\t%016x\t%016x\n" % row for row in rows)
        return hashlib.sha256(text.encode("ascii")).hexdigest()

    output = {
        "purpose": "TEST-ONLY exploratory Q120 integer Taylor comparison; not execution-path code",
        "input": "the exact binary64 x_raw_bits in Java fixture GRID rows",
        "range_reduction": "nearest-Q120 pi constant; x in [0,2*pi), subtract 2*pi when x > pi",
        "polynomial": "sin Taylor recurrence through n=30 (x^61 term), Q120 nearest-even rounded term recurrence",
        "conversion": "exact Fraction(total, 2^120) converted to binary64; float bits cast from that binary64",
        "grid_count": count,
        "pi_decimal_digits": len(PI_DECIMAL.replace(".", "")),
        "q_bits": Q_BITS,
        "double_bit_mismatch_count": len(mismatch_double),
        "double_mismatch_first_32": [row[0] for row in mismatch_double[:32]],
        "double_mismatch_records_sha256": mismatch_digest(mismatch_double),
        "float_cast_bit_mismatch_count": len(mismatch_float),
        "float_mismatch_first_32": [row[0] for row in mismatch_float[:32]],
        "float_mismatch_records_sha256": mismatch_digest(mismatch_float),
        "warning": "Exploratory approximation only; a mismatch or match says nothing by itself about genuine Minecraft inputs.",
    }
    print(json.dumps(output, sort_keys=True, indent=2, separators=(",", ": ")))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: explore_q120.py samples.tsv")
    main(sys.argv[1])
