import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.TreeMap;

/** Independent test-only bounded Q120 asin candidate; not guest execution code. */
public strictfp final class Q120AsinProbe {
    private static final int Q_BITS = 120;
    private static final BigInteger ONE = BigInteger.ONE;
    private static final BigInteger TWO = BigInteger.valueOf(2L);
    private static final BigInteger Q = ONE.shiftLeft(Q_BITS);
    private static final BigInteger HALF_Q = Q.shiftRight(1);
    private static final BigInteger PI_OVER_2_Q = new BigInteger("1921fb54442d18469898cc51701b83a", 16);
    private static final long ONE_BITS = 0x3ff0000000000000L;
    private static final long HALF_BITS = 0x3fe0000000000000L;
    private static final long TINY_CUTOFF_BITS = 0x3e40000000000000L; // 2^-27
    private static final BigInteger MAX_SIGNED_256 = ONE.shiftLeft(255);
    private static final Map<String, Integer> MAX_BITS = new TreeMap<String, Integer>();
    private static long sqrtCalls;
    private static long seriesCalls;
    private static long seriesTerms;

    private static void observe(String name, BigInteger value) {
        BigInteger magnitude = value.abs();
        if (magnitude.compareTo(MAX_SIGNED_256) >= 0) {
            throw new AssertionError("signed 256-bit bound exceeded at " + name + ": " + value.toString(16));
        }
        Integer old = MAX_BITS.get(name);
        int bits = magnitude.bitLength();
        if (old == null || bits > old.intValue()) MAX_BITS.put(name, Integer.valueOf(bits));
    }

    private static BigInteger roundEven(BigInteger numerator, BigInteger denominator, String name) {
        if (numerator.signum() < 0 || denominator.signum() <= 0) {
            throw new AssertionError("roundEven requires nonnegative numerator and positive denominator");
        }
        observe(name + ".numerator", numerator);
        observe(name + ".denominator", denominator);
        BigInteger[] qr = numerator.divideAndRemainder(denominator);
        BigInteger twiceRemainder = qr[1].shiftLeft(1);
        observe(name + ".twice-remainder", twiceRemainder);
        int cmp = twiceRemainder.compareTo(denominator);
        if (cmp > 0 || (cmp == 0 && qr[0].testBit(0))) {
            qr[0] = qr[0].add(ONE);
        }
        observe(name + ".quotient", qr[0]);
        return qr[0];
    }

    private static BigInteger mulQ(BigInteger a, BigInteger b, String name) {
        BigInteger product = a.multiply(b);
        observe(name + ".product", product);
        return roundEven(product, Q, name + ".divide-q");
    }

    /** Exact Q120 input conversion for the non-tiny supported range. */
    private static BigInteger positiveInputQ(long absBits) {
        int exponent = (int) ((absBits >>> 52) & 0x7ffL);
        long fraction = absBits & 0x000fffffffffffffL;
        if (exponent == 0 || exponent == 0x7ff) {
            throw new AssertionError("non-tiny supported input must be normal");
        }
        int shift = exponent - 955; // (significand * 2^(e-52)) * 2^120
        if (shift < 0) throw new AssertionError("input below exact Q120 conversion range");
        BigInteger significand = ONE.shiftLeft(52).add(BigInteger.valueOf(fraction));
        BigInteger result = significand.shiftLeft(shift);
        observe("input-q", result);
        return result;
    }

    /** The recurrence computes terms n=0..128, with each division rounded ties-to-even. */
    private static BigInteger asinSeries(BigInteger xQ) {
        if (xQ.signum() < 0 || xQ.compareTo(HALF_Q) > 0) {
            throw new AssertionError("series domain must be [0,1/2]");
        }
        seriesCalls++;
        BigInteger term = xQ;
        BigInteger sum = term;
        observe("series-term", term);
        observe("series-sum", sum);
        for (int n = 1; n <= 128; n++) {
            BigInteger firstPower = mulQ(term, xQ, "series-power-1");
            BigInteger secondPower = mulQ(firstPower, xQ, "series-power-2");
            long odd = 2L * n - 1L;
            BigInteger numerator = BigInteger.valueOf(odd * odd);
            BigInteger denominator = BigInteger.valueOf(2L * n * (2L * n + 1L));
            BigInteger scaled = secondPower.multiply(numerator);
            observe("series-ratio-product", scaled);
            term = roundEven(scaled, denominator, "series-ratio");
            sum = sum.add(term);
            observe("series-term", term);
            observe("series-sum", sum);
            seriesTerms++;
        }
        return sum;
    }

    /** Newton integer square root, corrected and checked to be exactly floor(sqrt(n)). */
    private static BigInteger sqrtFloor(BigInteger n) {
        if (n.signum() < 0) throw new AssertionError("negative square-root radicand");
        sqrtCalls++;
        if (n.signum() == 0) return BigInteger.ZERO;
        BigInteger x = ONE.shiftLeft((n.bitLength() + 1) / 2);
        observe("sqrt-iterate", x);
        while (true) {
            BigInteger quotient = n.divide(x);
            BigInteger y = x.add(quotient).shiftRight(1);
            observe("sqrt-newton-sum", x.add(quotient));
            observe("sqrt-iterate", y);
            if (y.compareTo(x) >= 0) break;
            x = y;
        }
        BigInteger square = x.multiply(x);
        observe("sqrt-square", square);
        while (square.compareTo(n) > 0) {
            x = x.subtract(ONE);
            square = x.multiply(x);
            observe("sqrt-square", square);
        }
        while (true) {
            BigInteger next = x.add(ONE);
            BigInteger nextSquare = next.multiply(next);
            observe("sqrt-next-square", nextSquare);
            if (nextSquare.compareTo(n) > 0) break;
            x = next;
            square = nextSquare;
        }
        BigInteger nextSquare = x.add(ONE).multiply(x.add(ONE));
        observe("sqrt-radicand", n);
        observe("sqrt-square", square);
        observe("sqrt-next-square", nextSquare);
        if (square.compareTo(n) > 0 || nextSquare.compareTo(n) <= 0) {
            throw new AssertionError("integer sqrt floor invariant failed");
        }
        return x;
    }

    /** Round a nonnegative Q120 integer to binary64, exactly nearest-even. */
    private static long qToDoubleBits(BigInteger magnitudeQ) {
        if (magnitudeQ.signum() < 0) throw new AssertionError("negative magnitude");
        if (magnitudeQ.signum() == 0) return 0L;
        int bitLength = magnitudeQ.bitLength();
        int exponent = bitLength - 1 - Q_BITS;
        int discarded = bitLength - 53;
        BigInteger significand;
        if (discarded > 0) {
            significand = roundEven(magnitudeQ, ONE.shiftLeft(discarded), "binary64-significand");
        } else {
            significand = magnitudeQ.shiftLeft(-discarded);
            observe("binary64-significand", significand);
        }
        if (significand.bitLength() > 53) {
            significand = significand.shiftRight(1);
            exponent++;
        }
        if (exponent < -1022 || exponent > 1023 || significand.bitLength() != 53) {
            throw new AssertionError("unexpected Q120 result range");
        }
        BigInteger hidden = ONE.shiftLeft(52);
        BigInteger fraction = significand.subtract(hidden);
        if (fraction.signum() < 0 || fraction.bitLength() > 52) {
            throw new AssertionError("invalid binary64 fraction");
        }
        long result = ((long) (exponent + 1023) << 52) | fraction.longValue();
        observe("binary64-result-significand", significand);
        return result;
    }

    /** null means the explicit refusal policy applies. */
    private static Long asin(long rawBits) {
        long absBits = rawBits & Long.MAX_VALUE;
        int exponent = (int) ((absBits >>> 52) & 0x7ffL);
        if (exponent == 0x7ff || absBits > ONE_BITS) return null;
        if (absBits == 0L || absBits <= TINY_CUTOFF_BITS) {
            // For 0<=x<=2^-27, 0<=asin(x)-x<=x^3/(6(1-x^2));
            // this is strictly below half an ulp of x, including subnormals.
            return Long.valueOf(rawBits);
        }

        BigInteger xQ = positiveInputQ(absBits); // every binary64 in this range is exact in Q120
        BigInteger resultQ;
        if (absBits <= HALF_BITS) {
            resultQ = asinSeries(xQ);
        } else if (absBits == ONE_BITS) {
            resultQ = PI_OVER_2_Q;
            observe("pi-over-two-q", resultQ);
        } else {
            BigInteger delta = Q.subtract(xQ);
            observe("endpoint-delta", delta);
            BigInteger yQ = roundEven(delta, TWO, "half-endpoint-delta");
            BigInteger radicand = yQ.multiply(Q);
            observe("sqrt-radicand", radicand);
            BigInteger rootQ = sqrtFloor(radicand);
            observe("sqrt-q", rootQ);
            BigInteger correction = asinSeries(rootQ);
            resultQ = PI_OVER_2_Q.subtract(correction.shiftLeft(1));
            observe("pi-over-two-q", PI_OVER_2_Q);
            observe("asin-result-q", resultQ);
            if (resultQ.signum() < 0) throw new AssertionError("negative endpoint-reduced result");
        }
        long positive = qToDoubleBits(resultQ);
        if ((rawBits & Long.MIN_VALUE) != 0) positive |= Long.MIN_VALUE;
        return Long.valueOf(positive);
    }

    private static BigInteger unsigned(long value) {
        BigInteger low = BigInteger.valueOf(value & Long.MAX_VALUE);
        return value < 0 ? low.setBit(63) : low;
    }

    private static BigInteger ordered(long bits) {
        long key = bits < 0 ? ~bits : bits ^ Long.MIN_VALUE;
        return unsigned(key);
    }

    private static BigInteger ulpDistance(long a, long b) {
        return ordered(a).subtract(ordered(b)).abs();
    }

    private static String hex64(long value) {
        return String.format(Locale.ROOT, "%016x", Long.valueOf(value));
    }

    private static String hex32(int value) {
        return String.format(Locale.ROOT, "%08x", Integer.valueOf(value));
    }

    private static long parseHex64(String value) { return Long.parseUnsignedLong(value, 16); }
    private static int parseHex32(String value) { return (int) Long.parseLong(value, 16); }

    private static BigDecimal exactDecimal(long positiveBits) {
        return new BigDecimal(Double.longBitsToDouble(positiveBits));
    }

    /** Independent exact-rational nearest-even check for qToDoubleBits. */
    private static boolean independentlyNearest(BigInteger n, long candidateBits) {
        BigDecimal target = new BigDecimal(n).divide(new BigDecimal(Q));
        BigDecimal candidate = exactDecimal(candidateBits);
        int side = target.compareTo(candidate);
        if (side == 0) return true;
        long lowBits;
        long highBits;
        if (side > 0) {
            lowBits = candidateBits;
            highBits = candidateBits + 1L;
        } else {
            if (candidateBits == 0L) return false;
            lowBits = candidateBits - 1L;
            highBits = candidateBits;
        }
        BigDecimal low = exactDecimal(lowBits);
        BigDecimal high = exactDecimal(highBits);
        BigDecimal midpoint = low.add(high).divide(BigDecimal.valueOf(2L));
        int midpointSide = target.compareTo(midpoint);
        if (midpointSide < 0) return candidateBits == lowBits;
        if (midpointSide > 0) return candidateBits == highBits;
        return (candidateBits & 1L) == 0L;
    }

    private static void verifyPiConstant() {
        String piDigits = "3.14159265358979323846264338327950288419716939937510582097494459230781640628620899862803482534211706798214808651328230664709384460955058223172535940812848111745028410270193852110555964462294895493038196";
        BigDecimal piTimesQOverTwo = new BigDecimal(piDigits)
                .multiply(new BigDecimal(Q)).divide(BigDecimal.valueOf(2L));
        BigInteger rounded = piTimesQOverTwo.setScale(0, BigDecimal.ROUND_HALF_EVEN).toBigIntegerExact();
        if (!rounded.equals(PI_OVER_2_Q)) throw new AssertionError("pi/2 Q120 literal mismatch");
    }

    private static void verifySqrtImplementation() {
        Random random = new Random(0x53515254313230L);
        for (int i = 0; i < 4096; i++) {
            BigInteger n = new BigInteger(240, random);
            BigInteger root = sqrtFloor(n);
            BigInteger square = root.multiply(root);
            BigInteger next = root.add(ONE).multiply(root.add(ONE));
            observe("sqrt-test-radicand", n);
            observe("sqrt-test-square", square);
            observe("sqrt-test-next-square", next);
            if (square.compareTo(n) > 0 || next.compareTo(n) <= 0) {
                throw new AssertionError("sqrt test failed at " + n.toString(16));
            }
        }
    }

    private static void verifyQToDouble() {
        Random random = new Random(0x5142494e36345445L);
        BigInteger[] named = {
            BigInteger.ZERO, ONE, TWO, Q.shiftRight(1), Q.subtract(ONE), Q,
            Q.add(ONE), Q.shiftLeft(1).subtract(ONE), Q.shiftLeft(1), PI_OVER_2_Q,
            Q.add(ONE.shiftLeft(67)), Q.add(ONE.shiftLeft(67).multiply(BigInteger.valueOf(3L))),
            Q.subtract(ONE.shiftLeft(67)), Q.subtract(ONE.shiftLeft(67).multiply(BigInteger.valueOf(3L)))
        };
        long checks = 0;
        for (BigInteger n : named) {
            long converted = qToDoubleBits(n);
            if (!independentlyNearest(n, converted)) throw new AssertionError("named Q120 conversion failed: " + n);
            checks++;
        }
        for (int i = 0; i < 4096; i++) {
            BigInteger n = new BigInteger(121, random);
            long converted = qToDoubleBits(n);
            if (!independentlyNearest(n, converted)) {
                throw new AssertionError("random Q120 conversion failed at " + n.toString(16));
            }
            checks++;
        }
        System.out.println("q120_to_binary64_exact_nearest_checks=" + checks);
    }

    private static String jsonEscape(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    private static void writeSummary(File file, long supported, long refused,
            long doubleMismatches, long floatMismatches, long monotonicViolations,
            BigInteger maxUlp, String worstInput, String oracleHash,
            long conversionChecks) throws Exception {
        BufferedWriter out = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(file), "UTF-8"));
        try {
            out.write("{\n");
            out.write("  \"algorithm\": \"Q120 nearest-even term recurrence; exact integer sqrt; pi/2 Q120 scalar\",\n");
            out.write("  \"supported_inputs\": " + supported + ",\n");
            out.write("  \"refused_controls\": " + refused + ",\n");
            out.write("  \"double_raw_mismatches\": " + doubleMismatches + ",\n");
            out.write("  \"float_cast_raw_mismatches\": " + floatMismatches + ",\n");
            out.write("  \"sampled_monotonicity_violations\": " + monotonicViolations + ",\n");
            out.write("  \"maximum_ulp_distance\": \"" + maxUlp.toString() + "\",\n");
            out.write("  \"maximum_ulp_input_bits\": \"" + worstInput + "\",\n");
            out.write("  \"sqrt_floor_random_checks\": 4096,\n");
            out.write("  \"q120_to_binary64_nearest_checks\": " + conversionChecks + ",\n");
            out.write("  \"series_calls\": " + seriesCalls + ",\n");
            out.write("  \"series_terms_after_initial\": " + seriesTerms + ",\n");
            out.write("  \"maximum_absolute_signed_intermediate_bit_lengths\": {\n");
            int index = 0;
            for (Map.Entry<String, Integer> e : MAX_BITS.entrySet()) {
                out.write("    \"" + jsonEscape(e.getKey()) + "\": " + e.getValue());
                out.write(++index == MAX_BITS.size() ? "\n" : ",\n");
            }
            out.write("  },\n");
            out.write("  \"signed_256_bound\": \"every observed absolute intermediate < 2^255\",\n");
            out.write("  \"input_oracle_sha256\": \"" + oracleHash + "\",\n");
            out.write("  \"support_policy\": \"finite |x|<=1; signed zero exact; |x|<=2^-27 returns input under half-ULP inequality\",\n");
            out.write("  \"refusal_policy\": \"nonfinite and finite |x|>1 return no value; no oracle value is evaluated for those controls\"\n");
            out.write("}\n");
        } finally {
            out.close();
        }
    }

    private static String sha256(File file) throws Exception {
        java.security.MessageDigest digest = java.security.MessageDigest.getInstance("SHA-256");
        FileInputStream in = new FileInputStream(file);
        try {
            byte[] buffer = new byte[32768];
            int n;
            while ((n = in.read(buffer)) >= 0) if (n > 0) digest.update(buffer, 0, n);
        } finally { in.close(); }
        StringBuilder out = new StringBuilder();
        for (byte b : digest.digest()) out.append(String.format(Locale.ROOT, "%02x", b & 255));
        return out.toString();
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("usage: Q120AsinProbe ORACLE.tsv MISMATCHES.tsv SUMMARY.json");
        File oracle = new File(args[0]);
        File mismatches = new File(args[1]);
        File summary = new File(args[2]);
        verifyPiConstant();
        verifySqrtImplementation();
        verifyQToDouble();

        long supported = 0, refused = 0, doubleMismatches = 0, floatMismatches = 0;
        long monotonicViolations = 0;
        Map<BigInteger, Long> outputsByOrderedInput = new TreeMap<BigInteger, Long>();
        BigInteger maxUlp = BigInteger.ZERO;
        String worstInput = "0000000000000000";
        FileInputStream in = new FileInputStream(oracle);
        BufferedReader reader = new BufferedReader(new InputStreamReader(in, "UTF-8"));
        BufferedWriter bad = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(mismatches), "UTF-8"));
        try {
            bad.write("categories\tinput_bits\texpected_asin_bits\tactual_asin_bits\tulp_distance\texpected_float_bits\tactual_float_bits\n");
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.length() == 0 || line.charAt(0) == '#') continue;
                if (line.startsWith("categories\t")) continue;
                String[] fields = line.split("\\t", -1);
                if (fields.length != 5) throw new AssertionError("malformed oracle row: " + line);
                long inputBits = parseHex64(fields[1]);
                Long actual = asin(inputBits);
                if ("SUPPORTED".equals(fields[2])) {
                    supported++;
                    if (actual == null) throw new AssertionError("candidate refused supported input " + fields[1]);
                    long expected = parseHex64(fields[3]);
                    int expectedFloat = parseHex32(fields[4]);
                    long actualBits = actual.longValue();
                    outputsByOrderedInput.put(ordered(inputBits), Long.valueOf(actualBits));
                    int actualFloat = Float.floatToRawIntBits((float) Double.longBitsToDouble(actualBits));
                    BigInteger ulps = ulpDistance(expected, actualBits);
                    if (ulps.compareTo(maxUlp) > 0) {
                        maxUlp = ulps;
                        worstInput = fields[1];
                    }
                    boolean doubleBad = expected != actualBits;
                    boolean floatBad = expectedFloat != actualFloat;
                    if (doubleBad || floatBad) {
                        if (doubleBad) doubleMismatches++;
                        if (floatBad) floatMismatches++;
                        bad.write(fields[0] + "\t" + fields[1] + "\t" + fields[3] + "\t" + hex64(actualBits)
                                + "\t" + ulps.toString() + "\t" + fields[4] + "\t" + hex32(actualFloat) + "\n");
                    }
                } else if ("REFUSE".equals(fields[2])) {
                    refused++;
                    if (actual != null) throw new AssertionError("candidate accepted refused control " + fields[1]);
                    if (!"-".equals(fields[3]) || !"-".equals(fields[4])) {
                        throw new AssertionError("oracle evaluated a refused control " + fields[1]);
                    }
                } else {
                    throw new AssertionError("unknown policy " + fields[2]);
                }
            }
        } finally {
            bad.close();
            reader.close();
        }
        BigInteger previousOutput = null;
        for (Long output : outputsByOrderedInput.values()) {
            BigInteger currentOutput = ordered(output.longValue());
            if (previousOutput != null && currentOutput.compareTo(previousOutput) < 0) {
                monotonicViolations++;
            }
            previousOutput = currentOutput;
        }
        writeSummary(summary, supported, refused, doubleMismatches, floatMismatches,
                monotonicViolations, maxUlp, worstInput, sha256(oracle), 4110L);
        System.out.println("supported=" + supported + " refused=" + refused
                + " double_raw_mismatches=" + doubleMismatches
                + " float_cast_raw_mismatches=" + floatMismatches
                + " sampled_monotonicity_violations=" + monotonicViolations
                + " max_ulp=" + maxUlp + " at=0x" + worstInput
                + " max_intermediate_abs_bits=" + MAX_BITS.values().toString());
    }
}
