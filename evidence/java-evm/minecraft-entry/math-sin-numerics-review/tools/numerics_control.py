#!/usr/bin/env python3
"""Independent TEST-ONLY Q120 Math.sin controls; no execution-path use."""
import argparse
import decimal
import hashlib
import json
import os
import struct

Q_BITS = 120
Q = 1 << Q_BITS
PI_Q = 4175892906503776358826876457663557747
PI_DECIMAL = (
    "3.14159265358979323846264338327950288419716939937510582097494459230781640628620899862803482534211706798214808651328230664709384460955058223172535940812848111745028410270193852110555964462294895493038196"
)
MAX_X_BITS = 0x401921FB54442D18
TINY_IDENTITY_BITS = 0x3E40000000000000  # 2^-27; see bounded proof in README.
MASK64 = (1 << 64) - 1
SIGN64 = 1 << 63
GRID_FIXTURE_SHA256 = "6001a5c714608ca9649b08b25eba27a3aa011f7c870a32ddae15ca330fefc058"
RANDOM_SEED = 0x6D61746873696E31
RANDOM_COUNT = 32768


def round_div_even(numerator, denominator):
    """Signed exact integer division, nearest with ties to even."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    sign = -1 if numerator < 0 else 1
    quotient, remainder = divmod(abs(numerator), denominator)
    twice = remainder * 2
    if twice > denominator or (twice == denominator and quotient & 1):
        quotient += 1
    return sign * quotient


def verify_pi_constant():
    with decimal.localcontext() as ctx:
        ctx.prec = 260
        scaled = decimal.Decimal(PI_DECIMAL) * decimal.Decimal(Q)
        expected = int(scaled.to_integral_value(rounding=decimal.ROUND_HALF_EVEN))
    if expected != PI_Q:
        raise AssertionError("pinned Q120 pi integer is not nearest-even pi")


def binary64_to_q120(raw):
    """Map the exact IEEE-754 input bit pattern to Q120 using integer fields."""
    sign = -1 if raw & SIGN64 else 1
    exponent = (raw >> 52) & 0x7FF
    fraction = raw & ((1 << 52) - 1)
    if exponent == 0x7FF:
        raise ValueError("non-finite input")
    if exponent == 0:
        significand = fraction
        power = -1074
    else:
        significand = (1 << 52) | fraction
        power = exponent - 1023 - 52
    shift = power + Q_BITS
    if shift >= 0:
        magnitude = significand << shift
    else:
        magnitude = round_div_even(significand, 1 << -shift)
    return sign * magnitude


def q120_to_binary64(value):
    """Exact integer-to-binary64 nearest-even conversion (Q120 values are normal)."""
    if value == 0:
        return 0
    signbit = SIGN64 if value < 0 else 0
    magnitude = abs(value)
    top = magnitude.bit_length() - 1
    exponent = top - Q_BITS
    shift = top - 52
    if shift > 0:
        significand = round_div_even(magnitude, 1 << shift)
    else:
        significand = magnitude << -shift
    if significand == (1 << 53):
        significand >>= 1
        exponent += 1
    exponent_field = exponent + 1023
    if exponent_field <= 0 or exponent_field >= 0x7FF:
        raise AssertionError("Q120 result escaped normal finite binary64 range")
    fraction = significand - (1 << 52)
    return signbit | (exponent_field << 52) | fraction


def sin_q120(raw, tracker=None):
    """Two-step recurrence from raw bits; optional exact multiplication telemetry."""
    magnitude_bits = raw & (SIGN64 - 1)
    if magnitude_bits > MAX_X_BITS:
        raise ValueError("finite |x| <= 6.283185307179586 required")
    exponent = (raw >> 52) & 0x7FF
    if exponent == 0x7FF:
        raise ValueError("non-finite input")
    # On this interval |sin(x)-x| <= |x|^3/6. For |x|<=2^-27 the
    # exact real result rounds to x; preserve its raw sign, including subnormals.
    if magnitude_bits <= TINY_IDENTITY_BITS:
        return raw

    x = binary64_to_q120(raw)
    if x > PI_Q:
        x -= 2 * PI_Q
    elif x < -PI_Q:
        x += 2 * PI_Q

    square_product = x * x
    record_product(tracker, square_product, "xq*xq", raw)
    x2 = round_div_even(square_product, Q)
    term = x
    total = x
    for n in range(1, 31):
        product = -term * x2
        record_product(tracker, product, "term*x2@n=%d" % n, raw)
        term = round_div_even(product, Q * (2 * n) * (2 * n + 1))
        total += term
    return q120_to_binary64(total)


def record_product(tracker, product, stage, raw):
    if tracker is None:
        return
    bits = abs(product).bit_length()
    if bits > tracker["max_bits"]:
        tracker.update({"max_bits": bits, "stage": stage, "x_raw_bits": "%016x" % raw})


def raw_float_bits_from_double(raw):
    value = struct.unpack(">d", struct.pack(">Q", raw))[0]
    return struct.unpack(">I", struct.pack(">f", value))[0]


def ordered_float_key(raw):
    return (~raw & MASK64) if raw & SIGN64 else (raw | SIGN64)


def ulp_distance(left, right):
    return abs(ordered_float_key(left) - ordered_float_key(right))


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_tsv(path, expected_header):
    with open(path, "r", encoding="ascii", newline="") as stream:
        header = stream.readline().rstrip("\n")
        if header != expected_header:
            raise SystemExit("unexpected TSV header in %s: %r" % (path, header))
        for line_number, line in enumerate(stream, 2):
            fields = line.rstrip("\n").split("\t")
            yield line_number, fields


def hex64(raw):
    return "%016x" % raw


def hex32(raw):
    return "%08x" % raw


def mismatch_digest(lines):
    return hashlib.sha256("".join(lines).encode("ascii")).hexdigest()


def check_grid(fixture, out_dir):
    expected_hash = sha256_file(fixture)
    if expected_hash != GRID_FIXTURE_SHA256:
        raise SystemExit("generated-grid fixture SHA256 changed: " + expected_hash)
    os.makedirs(out_dir, exist_ok=True)
    mismatches = []
    max_ulp = -1
    max_record = None
    product_tracker = {"max_bits": 0, "stage": None, "x_raw_bits": None}
    count = 0
    expected_index = 0
    mismatch_float_count = 0
    rows_seen = 0
    with open(os.path.join(out_dir, "grid-mismatches.tsv"), "w", encoding="ascii", newline="") as mismatch_file:
        mismatch_file.write("index\tx_raw_bits\tq120_raw_bits\tjdk8_raw_bits\tulp_distance\tq120_float_bits\tjdk8_float_bits\n")
        for line_number, fields in parse_tsv(fixture, "kind\tkey\tx_raw_bits\tmath_sin_raw_bits\tfloat_cast_raw_bits"):
            if len(fields) != 5:
                raise SystemExit("malformed grid fixture row %d" % line_number)
            if fields[0] != "GRID":
                continue
            index = int(fields[1])
            if index != expected_index:
                raise SystemExit("noncontiguous generated grid at index %d" % index)
            expected_index += 1
            raw = int(fields[2], 16)
            jdk = int(fields[3], 16)
            jdk_float = int(fields[4], 16)
            qraw = sin_q120(raw, product_tracker)
            qfloat = raw_float_bits_from_double(qraw)
            distance = ulp_distance(qraw, jdk)
            rows_seen += 1
            if distance > max_ulp:
                max_ulp = distance
                max_record = {"index": index, "x_raw_bits": hex64(raw), "q120_raw_bits": hex64(qraw), "jdk8_raw_bits": hex64(jdk)}
            if qraw != jdk:
                text = "%d\t%s\t%s\t%s\t%d\t%s\t%s\n" % (index, hex64(raw), hex64(qraw), hex64(jdk), distance, hex32(qfloat), hex32(jdk_float))
                mismatch_file.write(text)
                mismatches.append(text)
            if qfloat != jdk_float:
                mismatch_float_count += 1
            count += 1
    if count != 65536 or expected_index != 65536:
        raise SystemExit("expected 65536 contiguous GRID rows; got %d" % count)
    summary = {
        "purpose": "independent test-only two-step Q120 Taylor candidate versus existing generated OpenJDK 8 grid",
        "fixture_sha256": expected_hash,
        "grid_count": count,
        "q_bits": Q_BITS,
        "pi_q120": str(PI_Q),
        "range_reduction": "exact input bits to Q120; subtract/add 2*pi_Q when outside [-pi_Q,+pi_Q]",
        "recurrence": "x2=roundEven(x*x/Q); term_n=roundEven(-term_(n-1)*x2/(Q*(2n)*(2n+1))), n=1..30",
        "double_bit_mismatch_count": len(mismatches),
        "double_max_ulp_distance": max_ulp,
        "max_ulp_example": max_record,
        "double_mismatch_records_sha256": mismatch_digest(mismatches),
        "float_cast_bit_mismatch_count": mismatch_float_count,
        "intermediate_multiplication_max_signed_bit_length": product_tracker["max_bits"],
        "max_multiplication": product_tracker,
        "nonclaim": "finite generated probes only; no universal Math.sin correctness claim",
    }
    if max_ulp > 1 or mismatch_float_count != 0:
        raise SystemExit("grid control failed 1-ULP / float-exact expectation; see " + out_dir)
    write_json(os.path.join(out_dir, "grid-summary.json"), summary)
    return summary


def splitmix64_next(state):
    state = (state + 0x9E3779B97F4A7C15) & MASK64
    z = state
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
    z ^= z >> 31
    return state, z & MASK64


def generate_samples(path, random_count=RANDOM_COUNT):
    rows = []

    def add(kind, key, raw):
        magnitude = raw & (SIGN64 - 1)
        if magnitude > MAX_X_BITS or ((raw >> 52) & 0x7FF) == 0x7FF:
            raise AssertionError("sample generator made out-of-domain/nonfinite input")
        rows.append((kind, key, raw))

    def pair_neighbors(kind, label, center, offsets):
        for delta in offsets:
            mag = center + delta
            if 0 <= mag <= MAX_X_BITS:
                suffix = "center" if delta == 0 else ("m%02d" % -delta if delta < 0 else "p%02d" % delta)
                add(kind, label + "-pos-" + suffix, mag)
                add(kind, label + "-neg-" + suffix, SIGN64 | mag)

    add("zero", "positive-zero", 0)
    add("zero", "negative-zero", SIGN64)
    # Previously measured nonzero argument, included only as a generated oracle control.
    add("prior-measured-x1-control", "0x3f1921fb54442d18-not-replayed", 0x3F1921FB54442D18)
    for mag in (1, 2, 3, 7, 0x000FFFFFFFFFFFFF, 0x0010000000000000,
                0x0010000000000001):
        add("subnormal-edge", "pos-%016x" % mag, mag)
        add("subnormal-edge", "neg-%016x" % mag, SIGN64 | mag)
    pair_neighbors("tiny-identity-boundary", "2^-27", TINY_IDENTITY_BITS, range(-3, 4))
    for raw_center, label, radius in (
        (0x3FF921FB54442D18, "pi-over-2", 3),
        (0x400921FB54442D18, "pi", 8),
        (MAX_X_BITS, "two-pi-input-bound", 8),
    ):
        pair_neighbors("near-special", label, raw_center, range(-radius, radius + 1))
    for center, label in ((0x3FF0000000000000, "one"),
                          (0x4018000000000000, "six")):
        pair_neighbors("finite-boundary", label, center, (-1, 0, 1))

    state = RANDOM_SEED
    random_rows = []
    while len(random_rows) < random_count:
        state, candidate = splitmix64_next(state)
        magnitude = candidate & (SIGN64 - 1)
        if magnitude > MAX_X_BITS:
            continue
        state, sign_random = splitmix64_next(state)
        raw = magnitude | (SIGN64 if sign_random >> 63 else 0)
        random_rows.append(("random", "splitmix64-%05d" % len(random_rows), raw))
    rows.extend(random_rows)

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="ascii", newline="") as stream:
        stream.write("kind\tkey\tx_raw_bits\n")
        for kind, key, raw in rows:
            stream.write("%s\t%s\t%s\n" % (kind, key, hex64(raw)))
    unique = len(set(raw for _, _, raw in rows))
    summary = {
        "purpose": "generated finite-domain JDK8 oracle sample list; no original program input claim",
        "seed": "0x%016x" % RANDOM_SEED,
        "PRNG": "SplitMix64 with rejection sampling over monotone finite raw magnitudes [0,0x%016x], independent random sign bit" % MAX_X_BITS,
        "random_count": random_count,
        "edge_count": len(rows) - random_count,
        "total_count": len(rows),
        "unique_raw_inputs": unique,
        "duplicate_raw_rows": len(rows) - unique,
        "domain": "finite raw magnitude <= 0x%016x (6.283185307179586 binary64 bound)" % MAX_X_BITS,
        "input_sha256": sha256_file(path),
    }
    return summary


def compare_generated(inputs_path, oracle_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    inputs = list(parse_tsv(inputs_path, "kind\tkey\tx_raw_bits"))
    oracle = list(parse_tsv(oracle_path, "kind\tkey\tx_raw_bits\tjdk_sin_raw_bits\tjdk_float_raw_bits"))
    if len(inputs) != len(oracle):
        raise SystemExit("oracle row count differs from generated input count")
    mismatch_records = []
    grouped = {}
    max_ulp = -1
    max_record = None
    tracker = {"max_bits": 0, "stage": None, "x_raw_bits": None}
    with open(os.path.join(out_dir, "sample-comparison.tsv"), "w", encoding="ascii", newline="") as output:
        output.write("kind\tkey\tx_raw_bits\tq120_sin_raw_bits\tjdk8_sin_raw_bits\tulp_distance\tq120_float_raw_bits\tjdk8_float_raw_bits\tdouble_match\tfloat_match\n")
        for (in_line, inf), (oracle_line, outf) in zip(inputs, oracle):
            if len(inf) != 3 or len(outf) != 5 or inf[:3] != outf[:3]:
                raise SystemExit("input/oracle mismatch at row %d/%d" % (in_line, oracle_line))
            kind, key, raw_hex = inf
            raw = int(raw_hex, 16)
            qraw = sin_q120(raw, tracker)
            jdk = int(outf[3], 16)
            jdk_float = int(outf[4], 16)
            qfloat = raw_float_bits_from_double(qraw)
            distance = ulp_distance(qraw, jdk)
            double_match = qraw == jdk
            float_match = qfloat == jdk_float
            group = grouped.setdefault(kind, {"count": 0, "double_bit_mismatch_count": 0,
                                               "float_cast_bit_mismatch_count": 0,
                                               "max_ulp_distance": 0})
            group["count"] += 1
            group["double_bit_mismatch_count"] += int(not double_match)
            group["float_cast_bit_mismatch_count"] += int(not float_match)
            group["max_ulp_distance"] = max(group["max_ulp_distance"], distance)
            if distance > max_ulp:
                max_ulp = distance
                max_record = {"kind": kind, "key": key, "x_raw_bits": raw_hex,
                              "q120_raw_bits": hex64(qraw), "jdk8_raw_bits": hex64(jdk)}
            row = "%s\t%s\t%s\t%s\t%s\t%d\t%s\t%s\t%d\t%d\n" % (
                kind, key, raw_hex, hex64(qraw), hex64(jdk), distance,
                hex32(qfloat), hex32(jdk_float), int(double_match), int(float_match))
            output.write(row)
            if not double_match or not float_match:
                mismatch_records.append(row)
    double_count = sum(v["double_bit_mismatch_count"] for v in grouped.values())
    float_count = sum(v["float_cast_bit_mismatch_count"] for v in grouped.values())
    summary = {
        "purpose": "test-only Q120 comparison to JDK8 Math.sin for fixed edges and deterministic generated finite samples",
        "input_sha256": sha256_file(inputs_path),
        "oracle_sha256": sha256_file(oracle_path),
        "total_count": len(inputs),
        "group_counts": grouped,
        "double_bit_mismatch_count": double_count,
        "double_max_ulp_distance": max_ulp,
        "max_ulp_example": max_record,
        "float_cast_bit_mismatch_count": float_count,
        "mismatch_records_sha256": mismatch_digest(mismatch_records),
        "mismatch_rows_file": "sample-comparison.tsv (all rows, match flags, raw bits and ULP distances)",
        "intermediate_multiplication_max_signed_bit_length": tracker["max_bits"],
        "max_multiplication": tracker,
        "near_special_caveats": [
            "Near pi and 2*pi, exact raw-bit equality is highly sensitive to reduction and implementation details; counts are measurements of this finite set only.",
            "Java 8 Math.sin is not specified as universally correctly rounded; a match or <=1 ULP sample result is not a proof for all inputs.",
            "The generated random raw-bit distribution and edge rows are controls, not evidence that unchanged Minecraft supplied these values.",
        ],
    }
    write_json(os.path.join(out_dir, "sample-summary.json"), summary)
    return summary


def overflow_report(grid_summary, sample_summary):
    measured = max(grid_summary["intermediate_multiplication_max_signed_bit_length"],
                   sample_summary["intermediate_multiplication_max_signed_bit_length"])
    return {
        "status": "bounded algebraic estimate for the specified finite domain and recurrence; not a universal sine-correctness proof",
        "assumptions": [
            "Input is finite and raw magnitude <= 0x401921fb54442d18 (the specified binary64 6.283185307179586 bound).",
            "Range reduction uses nearest-Q120 input conversion and pi_Q=roundEven(pi*2^120); the one-step +/-2*pi_Q reduction leaves |xq| < (13/4)*Q.",
            "Q=2^120, x2=roundEven(xq*xq/Q), and each term is rounded by nearest-even division using denominator Q*(2n)*(2n+1), n=1..30.",
        ],
        "algebraic_bounds": {
            "Q": "2^120",
            "reduced_abs_xq": "< (13/4) Q",
            "x2": "< 11 Q (since (13/4)^2 < 11; rounding adds <= 1/2 Q-unit)",
            "term_n": "< 7 Q for n=1..30: n=1 <= (13/4*11/6 + 1/2)Q < 7Q; for n>=2 ratio <=11/20 and +1/2 rounding remains <7Q",
            "sum_abs": "< (13/4 + 30*7)Q < 214Q < 2^128",
            "xq_squared_product": "< (13/4)^2 Q^2 < 16 Q^2 = 2^244",
            "term_times_x2_product": "< 7*11 Q^2 = 77 Q^2 < 128 Q^2 = 2^247",
            "largest_signed_256_product_bound": "<2^247, below signed int256 max 2^255-1 (at least 8 exponent bits of headroom)",
            "largest_recurrence_denominator": "Q*(60*61) = 3660*2^120 < 2^132",
        },
        "measured": {
            "grid_max_signed_product_bit_length": grid_summary["intermediate_multiplication_max_signed_bit_length"],
            "generated_sample_max_signed_product_bit_length": sample_summary["intermediate_multiplication_max_signed_bit_length"],
            "combined_max_signed_product_bit_length": measured,
        },
        "warning": "These bounds concern arithmetic intermediates only. They do not establish approximation error, correct rounding, JDK8 agreement for all finite inputs, nor behavior outside the stated domain.",
    }


def write_json(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="ascii", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def main():
    verify_pi_constant()
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_prepare = sub.add_parser("prepare")
    p_prepare.add_argument("--out", required=True)
    p_prepare.add_argument("--random-count", type=int, default=RANDOM_COUNT)
    p_grid = sub.add_parser("grid")
    p_grid.add_argument("--fixture", required=True)
    p_grid.add_argument("--out-dir", required=True)
    p_compare = sub.add_parser("compare")
    p_compare.add_argument("--inputs", required=True)
    p_compare.add_argument("--oracle", required=True)
    p_compare.add_argument("--out-dir", required=True)
    p_overflow = sub.add_parser("overflow")
    p_overflow.add_argument("--grid", required=True)
    p_overflow.add_argument("--samples", required=True)
    p_overflow.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = generate_samples(args.out, args.random_count)
    elif args.command == "grid":
        result = check_grid(args.fixture, args.out_dir)
    elif args.command == "compare":
        result = compare_generated(args.inputs, args.oracle, args.out_dir)
    else:
        with open(args.grid, "r", encoding="ascii") as stream:
            grid_summary = json.load(stream)
        with open(args.samples, "r", encoding="ascii") as stream:
            sample_summary = json.load(stream)
        result = overflow_report(grid_summary, sample_summary)
        write_json(args.out, result)
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
