#!/usr/bin/env python3
"""TEST-ONLY Q120 integer cosine model; no host libm or guest-runtime calls."""
import decimal
import fractions
import hashlib
import json
import sys

Q_BITS = 120
Q = 1 << Q_BITS
PI_Q = 4175892906503776358826876457663557747
PI_BITS = 0x400921FB54442D18
BOUND_BITS = 0x401921FB54442D18
TINY_BITS = 0x3E40000000000000  # 2^-27: 1-cos(x) <= x^2/2 <= 2^-55
MASK64 = (1 << 64) - 1
SIGN64 = 1 << 63
MAX_INTERMEDIATE_BITS = {}


def observe(name, value):
    bits = abs(value).bit_length()
    if bits > MAX_INTERMEDIATE_BITS.get(name, 0):
        MAX_INTERMEDIATE_BITS[name] = bits


def round_div_even(numerator, denominator):
    """Exact signed integer division, nearest with ties to even."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    observe("round.input-numerator", numerator)
    observe("round.denominator", denominator)
    sign = -1 if numerator < 0 else 1
    quotient, remainder = divmod(abs(numerator), denominator)
    twice_remainder = remainder << 1
    observe("round.quotient-before", quotient)
    observe("round.remainder", remainder)
    observe("round.twice-remainder", twice_remainder)
    cmp = twice_remainder - denominator
    observe("round.tie-comparison-difference", cmp)
    if cmp > 0 or (cmp == 0 and quotient & 1):
        quotient += 1
    observe("round.quotient-after", quotient)
    return sign * quotient


def input_q120(abs_bits, negative):
    exponent = (abs_bits >> 52) & 0x7FF
    fraction = abs_bits & ((1 << 52) - 1)
    if exponent == 0 or exponent == 0x7FF:
        raise AssertionError("non-tiny accepted input must be finite normal")
    significand = (1 << 52) | fraction
    observe("input-significand", significand)
    # x = significand * 2^(exponent - 1023 - 52); multiply by 2^120.
    shift = exponent - 955
    if shift < 0:
        raise AssertionError("tiny input escaped the proven 2^-27 shortcut")
    result = significand << shift
    observe("input-q", result)
    return -result if negative else result


def q120_to_binary64(value):
    if value == 0:
        return 0  # The modeled cosine is positive at signed zero and tiny inputs.
    sign = SIGN64 if value < 0 else 0
    magnitude = abs(value)
    observe("binary64-conversion-input-q", magnitude)
    bit_length = magnitude.bit_length()
    exponent = bit_length - 1 - Q_BITS
    if exponent < -1022:
        # A Q120 integer's least nonzero magnitude is 2^-120, hence normal.
        raise AssertionError("unexpected Q120 subnormal conversion")
    shift = bit_length - 53
    if shift > 0:
        significand = round_div_even(magnitude, 1 << shift)
    else:
        significand = magnitude << -shift
    observe("binary64-output-significand", significand)
    if significand == (1 << 53):
        significand >>= 1
        exponent += 1
    if not (1 << 52) <= significand < (1 << 53):
        raise AssertionError("bad normalized significand")
    if exponent > 1023:
        return sign | (0x7FF << 52)
    return sign | ((exponent + 1023) << 52) | (significand - (1 << 52))


def binary64_to_binary32(bits):
    """Exact nearest-even Java-style float cast, directly from binary64 bits."""
    sign = (bits >> 32) & 0x80000000
    exponent_field = (bits >> 52) & 0x7FF
    fraction = bits & ((1 << 52) - 1)
    if exponent_field == 0x7FF:
        if fraction == 0:
            return sign | 0x7F800000
        payload = fraction >> 29
        return sign | 0x7F800000 | (payload if payload else 1)
    if exponent_field == 0 and fraction == 0:
        return sign
    if exponent_field == 0:
        # Every nonzero binary64 subnormal is below half a binary32 subnormal.
        return sign
    exponent = exponent_field - 1023
    significand = (1 << 52) | fraction
    if exponent >= -126:
        rounded = round_div_even(significand, 1 << 29)
        if rounded == 1 << 24:
            rounded >>= 1
            exponent += 1
        if exponent > 127:
            return sign | 0x7F800000
        return sign | ((exponent + 127) << 23) | (rounded - (1 << 23))
    # Binary32 subnormal units are 2^-149.
    shift = -(exponent + 97)
    rounded = (round_div_even(significand, 1 << shift)
               if shift > 0 else significand << -shift)
    if rounded >= 1 << 23:
        return sign | (1 << 23)
    return sign | rounded


def cosine_q120(input_bits):
    sign = bool(input_bits & SIGN64)
    magnitude = input_bits & (SIGN64 - 1)
    exponent = (magnitude >> 52) & 0x7FF
    if exponent == 0x7FF or magnitude > BOUND_BITS:
        raise ValueError("REFUSE control must not enter numerical model")
    if magnitude <= TINY_BITS:
        # Includes both signed zeros; the bound is strictly inside half an ulp below 1.
        return 0x3FF0000000000000

    xq = input_q120(magnitude, sign)
    period = 2 * PI_Q
    observe("period-2pi-q", period)
    turns = round_div_even(xq, period)
    observe("range-reduction-turn-count", turns)
    reduced = xq - turns * period
    observe("range-reduced-x-q", reduced)
    if abs(reduced) > PI_Q:
        raise AssertionError("nearest-even period reduction escaped [-piQ, piQ]")

    # Keep each product <= about 245 bits: first square into Q120, then recur.
    square_product = reduced * reduced
    observe("x-square-product", square_product)
    x2 = round_div_even(square_product, Q)
    observe("x-squared-q", x2)
    term = Q
    total = Q
    observe("taylor-initial-term", term)
    observe("taylor-initial-sum", total)
    for n in range(1, 31):
        factor = (2 * n - 1) * (2 * n)
        numerator = -term * x2
        observe("taylor-term-product", numerator)
        denominator = Q * factor
        observe("taylor-term-denominator", denominator)
        term = round_div_even(numerator, denominator)
        total += term
        observe("taylor-term", term)
        observe("taylor-partial-sum", total)
    return q120_to_binary64(total)


def raw64(hex_bits):
    return int(hex_bits, 16)


def ordered64(bits):
    return (~bits & MASK64) if bits & SIGN64 else (bits ^ SIGN64)


def hex64(bits):
    return "%016x" % bits


def hex32(bits):
    return "%08x" % bits


def tail_bound():
    # Alternating-series remainder after n=30: |x|^62/62!, |x|<=pi<22/7.
    factorial = 1
    for value in range(2, 63):
        factorial *= value
    bound = fractions.Fraction(22, 7) ** 62 / factorial
    with decimal.localcontext() as context:
        context.prec = 40
        decimal_bound = decimal.Decimal(bound.numerator) / decimal.Decimal(bound.denominator)
        decimal_text = "%.12E" % decimal_bound
    power = 0
    while bound < fractions.Fraction(1, 1 << (power + 1)):
        power += 1
    return decimal_text, power, str(bound.numerator), str(bound.denominator)


def run(path, out_path, mismatch_path, summary_path):
    rows = []
    with open(path, "r", encoding="ascii", newline="") as fixture:
        header = fixture.readline().rstrip("\n")
        expected_header = "categories\tinput_bits\tpolicy\tjava8_cos_bits\tjava8_float_bits"
        if header != expected_header:
            raise SystemExit("unexpected Java fixture header: " + header)
        for line_number, line in enumerate(fixture, 2):
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 5:
                raise SystemExit("bad fixture row %d" % line_number)
            categories, input_hex, policy, java_hex, java_float_hex = fields
            bits = raw64(input_hex)
            magnitude = bits & (SIGN64 - 1)
            exponent = (magnitude >> 52) & 0x7FF
            expected_policy = "SUPPORTED" if exponent != 0x7FF and magnitude <= BOUND_BITS else "REFUSE"
            if policy != expected_policy:
                raise SystemExit("policy mismatch at input " + input_hex)
            if policy == "REFUSE":
                if java_hex != "-" or java_float_hex != "-":
                    raise SystemExit("refused controls must have no Java result")
                rows.append((categories, input_hex, policy, "-", "-", "-", "-", "-"))
                continue

            java_bits = raw64(java_hex)
            java_float = int(java_float_hex, 16)
            q_bits = cosine_q120(bits)
            q_float = binary64_to_binary32(q_bits)
            distance = abs(ordered64(q_bits) - ordered64(java_bits))
            rows.append((categories, input_hex, policy, java_hex, java_float_hex,
                         hex64(q_bits), hex32(q_float), str(distance)))

    supported = [r for r in rows if r[2] == "SUPPORTED"]
    refused = len(rows) - len(supported)
    mismatches = [r for r in supported if r[3] != r[5] or r[4] != r[6]]
    double_mismatches = [r for r in supported if r[3] != r[5]]
    float_mismatches = [r for r in supported if r[4] != r[6]]
    max_row = max(supported, key=lambda r: int(r[7]))
    max_ulp = int(max_row[7])

    with open(out_path, "w", encoding="ascii", newline="\n") as out:
        out.write("categories\tinput_bits\tpolicy\tjava8_cos_bits\tjava8_float_bits\tq120_cos_bits\tq120_float_bits\tulp_distance\n")
        for row in rows:
            out.write("\t".join(row) + "\n")
    with open(mismatch_path, "w", encoding="ascii", newline="\n") as out:
        out.write("categories\tinput_bits\tjava8_cos_bits\tq120_cos_bits\tulp_distance\tjava8_float_bits\tq120_float_bits\n")
        for row in mismatches:
            out.write("\t".join((row[0], row[1], row[3], row[5], row[7], row[4], row[6])) + "\n")

    grid = []
    for row in supported:
        if "grid-2pi-over-65536:" in row[0]:
            index = int(row[0].split("grid-2pi-over-65536:", 1)[1].split(",", 1)[0])
            grid.append((index, int(row[3], 16), int(row[5], 16)))
    grid.sort()
    if len(grid) != 65536 or any(grid[i][0] != i for i in range(len(grid))):
        raise AssertionError("hypothetical generated grid was not complete")
    # Split at the raw binary64 approximation to pi, noting the true pi lies slightly above it.
    # Grid rows are inserted in their generation order; recover input bits from the fixture.
    input_by_grid = {}
    with open(path, "r", encoding="ascii", newline="") as fixture:
        fixture.readline()
        for line in fixture:
            categories, input_hex, policy, _, _ = line.rstrip("\n").split("\t")
            if "grid-2pi-over-65536:" in categories:
                index = int(categories.split("grid-2pi-over-65536:", 1)[1].split(",", 1)[0])
                input_by_grid[index] = int(input_hex, 16)
    pi_index = max(i for i in range(65536) if input_by_grid[i] <= PI_BITS)

    def monotonicity(values, increasing):
        violations = 0
        for left, right in zip(values, values[1:]):
            a, b = ordered64(left), ordered64(right)
            if (b < a) if increasing else (b > a):
                violations += 1
        return violations

    java_first = [entry[1] for entry in grid[:pi_index + 1]]
    java_second = [entry[1] for entry in grid[pi_index + 1:]]
    q_first = [entry[2] for entry in grid[:pi_index + 1]]
    q_second = [entry[2] for entry in grid[pi_index + 1:]]
    monotonic = {
        "grid_rows": len(grid),
        "split_index_last_raw_input_le_nearest_binary64_pi": pi_index,
        "java8_decreasing_side_violations": monotonicity(java_first, False),
        "java8_increasing_side_violations": monotonicity(java_second, True),
        "q120_decreasing_side_violations": monotonicity(q_first, False),
        "q120_increasing_side_violations": monotonicity(q_second, True),
        "caveat": "sampled only on the 65536-point positive grid; the split uses nearest binary64 pi, not an exhaustive real-domain proof"
    }

    # Check even symmetry wherever both signs of the same raw magnitude occur.
    output_map = {}
    for row in supported:
        bits = int(row[1], 16)
        output_map[bits] = (int(row[3], 16), int(row[5], 16))
    symmetry_pairs = 0
    java_symmetry_mismatches = 0
    q_symmetry_mismatches = 0
    for bits, (java, qbits) in list(output_map.items()):
        mirror = bits ^ SIGN64
        if mirror in output_map and not bits & SIGN64:
            symmetry_pairs += 1
            if output_map[mirror][0] != java:
                java_symmetry_mismatches += 1
            if output_map[mirror][1] != qbits:
                q_symmetry_mismatches += 1

    tail_decimal, tail_pow2, tail_num, tail_den = tail_bound()
    max_bits = max(MAX_INTERMEDIATE_BITS.values()) if MAX_INTERMEDIATE_BITS else 0
    summary = {
        "model": "Q120 signed integer cosine; no host libm, Decimal trig, or binary64 arithmetic in cosine evaluation",
        "q_bits": Q_BITS,
        "pi_q": str(PI_Q),
        "pi_q_source": "task-pinned nearest-even Q120 constant",
        "input_domain": "finite |x|<=raw 0x401921fb54442d18; all other rows are REFUSE controls",
        "supported_rows": len(supported),
        "refused_controls": refused,
        "double_raw_bit_mismatches_vs_openjdk8": len(double_mismatches),
        "float_cast_raw_bit_mismatches_vs_openjdk8": len(float_mismatches),
        "maximum_ulp_distance_vs_openjdk8": max_ulp,
        "maximum_ulp_witness": {
            "input_bits": max_row[1], "categories": max_row[0],
            "java8_bits": max_row[3], "q120_bits": max_row[5], "ulp_distance": max_ulp
        },
        "double_mismatch_records_sha256": hashlib.sha256("".join("\t".join((r[1], r[3], r[5], r[7])) + "\n" for r in double_mismatches).encode("ascii")).hexdigest(),
        "float_mismatch_records_sha256": hashlib.sha256("".join("\t".join((r[1], r[4], r[6])) + "\n" for r in float_mismatches).encode("ascii")).hexdigest(),
        "sampled_monotonicity": monotonic,
        "even_symmetry": {
            "signed_pairs_compared": symmetry_pairs,
            "java8_raw_mismatches": java_symmetry_mismatches,
            "q120_raw_mismatches": q_symmetry_mismatches
        },
        "n30_taylor_tail_bound": {
            "first_omitted_term": "|x|^62/62! for |x|<=pi",
            "rational_upper_bound": "(22/7)^62/62! = %s/%s" % (tail_num, tail_den),
            "decimal_upper_bound": tail_decimal,
            "strictly_less_than": "2^-%d" % tail_pow2,
            "alternating_series_note": "terms decrease on |x|<=pi for the omitted tail; this bounds truncation only, not Q120 rounding/input-reduction error"
        },
        "maximum_absolute_intermediate_bit_length": max_bits,
        "maximum_intermediate_bit_lengths": dict(sorted(MAX_INTERMEDIATE_BITS.items())),
        "signed_256_product_bound": {
            "maximum_observed_product_bits": max(MAX_INTERMEDIATE_BITS.get("x-square-product", 0), MAX_INTERMEDIATE_BITS.get("taylor-term-product", 0)),
            "strictly_below_255_bits": max(MAX_INTERMEDIATE_BITS.get("x-square-product", 0), MAX_INTERMEDIATE_BITS.get("taylor-term-product", 0)) < 255,
            "scope": "observed generated inputs only; report includes all recorded Python integer intermediates"
        },
        "conversion_and_range_reduction": "exact raw-binary64 decode to Q120 after tiny shortcut; nearest-even integer turns by 2*piQ; nearest-even Q120 recurrence n=1..30; integer nearest-even binary64 and binary32 conversion",
        "caveats": [
            "All non-grid vectors are generated controls, not observed subsequent original Minecraft arguments.",
            "OpenJDK 8 Math.cos is the host reference; Java permits semi-monotonic rather than universally correctly-rounded results.",
            "A finite sample with small ULP distance is not a global proof and is not an execution-path implementation."
        ]
    }
    with open(summary_path, "w", encoding="ascii", newline="\n") as out:
        json.dump(summary, out, indent=2, sort_keys=True)
        out.write("\n")
    print("supported=%d refused=%d double_mismatches=%d float_mismatches=%d max_ulp=%d max_intermediate_bits=%d grid_monotonic_violations(java=%d,q120=%d)" % (
        len(supported), refused, len(double_mismatches), len(float_mismatches), max_ulp,
        max_bits,
        monotonic["java8_decreasing_side_violations"] + monotonic["java8_increasing_side_violations"],
        monotonic["q120_decreasing_side_violations"] + monotonic["q120_increasing_side_violations"]))
    print("max_ulp_input=0x%s java8=0x%s q120=0x%s" % (max_row[1], max_row[3], max_row[5]))
    print("n30_tail<%s (<2^-%d); max product bits=%d" % (tail_decimal, tail_pow2, summary["signed_256_product_bound"]["maximum_observed_product_bits"]))


def self_test():
    assert round_div_even(5, 2) == 2
    assert round_div_even(7, 2) == 4
    assert round_div_even(-5, 2) == -2
    assert round_div_even(-7, 2) == -4
    assert q120_to_binary64(Q) == 0x3FF0000000000000
    # Q120 values exactly halfway between adjacent binary64 values around 1.
    half_ulp_q = 1 << 67
    assert q120_to_binary64(Q + half_ulp_q) == 0x3FF0000000000000
    assert q120_to_binary64(Q + 3 * half_ulp_q) == 0x3FF0000000000002
    assert q120_to_binary64(-(Q + half_ulp_q)) == 0xBFF0000000000000
    # Binary64 values exactly halfway between binary32 values around 1.
    assert binary64_to_binary32(0x3FF0000010000000) == 0x3F800000
    assert binary64_to_binary32(0x3FF0000030000000) == 0x3F800002
    assert cosine_q120(0) == 0x3FF0000000000000
    assert cosine_q120(SIGN64) == 0x3FF0000000000000
    assert binary64_to_binary32(0x3FF0000000000000) == 0x3F800000


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("usage: q120_cos.py JAVA8_ORACLE.tsv Q120.tsv MISMATCHES.tsv SUMMARY.json")
    self_test()
    run(*sys.argv[1:])
