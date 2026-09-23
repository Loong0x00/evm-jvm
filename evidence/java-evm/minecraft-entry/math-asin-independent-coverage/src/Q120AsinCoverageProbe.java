import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.TreeMap;

/** Test-only integer-Q120 controls; intentionally not linked to guest execution. */
public strictfp final class Q120AsinCoverageProbe {
    private static final int Q_BITS = 120;
    private static final int[] LIMITS = {32, 64, 128};
    private static final BigInteger ONE = BigInteger.ONE;
    private static final BigInteger TWO = BigInteger.valueOf(2L);
    private static final BigInteger Q = ONE.shiftLeft(Q_BITS);
    private static final BigInteger HALF_Q = Q.shiftRight(1);
    private static final BigInteger PI_OVER_2_Q = new BigInteger("1921fb54442d18469898cc51701b83a", 16);
    private static final long ONE_BITS = 0x3ff0000000000000L;
    private static final long HALF_BITS = 0x3fe0000000000000L;
    private static final long TINY_BITS = 0x3e40000000000000L;
    private static final BigInteger SIGNED_256_LIMIT = ONE.shiftLeft(255);

    private static final class Tracker {
        final int limit;
        final Map<String, Integer> bitsByOperation = new TreeMap<String, Integer>();
        int maxBits;
        String maxOperation = "none";
        Tracker(int limit) { this.limit = limit; }
        void observe(String name, BigInteger value) {
            BigInteger magnitude = value.abs();
            if (magnitude.compareTo(SIGNED_256_LIMIT) >= 0) {
                throw new AssertionError("signed 256-bit bound exceeded at " + name + ": " + value.toString(16));
            }
            int bits = magnitude.bitLength();
            Integer previous = bitsByOperation.get(name);
            if (previous == null || bits > previous.intValue()) bitsByOperation.put(name, Integer.valueOf(bits));
            if (bits > maxBits) { maxBits = bits; maxOperation = name; }
        }
    }

    private static final Tracker[] TRACKERS = {
        new Tracker(32), new Tracker(64), new Tracker(128)
    };
    private static final Map<Long, long[]> POSITIVE_CACHE = new HashMap<Long, long[]>();
    private static boolean measure = false;
    private static long seriesCalls;
    private static long recurrenceUpdates;
    private static long kernelEvaluations;

    private static final class Sample {
        final String categories;
        final long input;
        final boolean supported;
        final long expected;
        final int expectedFloat;
        long[] actual;
        Sample(String categories, long input, boolean supported, long expected, int expectedFloat) {
            this.categories = categories;
            this.input = input;
            this.supported = supported;
            this.expected = expected;
            this.expectedFloat = expectedFloat;
        }
    }

    private static void observe(String name, BigInteger value, Tracker only, int step) {
        if (only != null) {
            only.observe(name, value);
        } else if (measure) {
            for (Tracker tracker : TRACKERS) {
                if (step == 0 || step <= tracker.limit) tracker.observe(name, value);
            }
        }
    }

    private static BigInteger roundEven(BigInteger numerator, BigInteger denominator,
            String name, int step) {
        if (numerator.signum() < 0 || denominator.signum() <= 0) {
            throw new AssertionError("roundEven requires nonnegative numerator and positive denominator");
        }
        observe(name + ".numerator", numerator, null, step);
        observe(name + ".denominator", denominator, null, step);
        BigInteger[] qr = numerator.divideAndRemainder(denominator);
        BigInteger twiceRemainder = qr[1].shiftLeft(1);
        observe(name + ".twice-remainder", twiceRemainder, null, step);
        int cmp = twiceRemainder.compareTo(denominator);
        if (cmp > 0 || (cmp == 0 && qr[0].testBit(0))) qr[0] = qr[0].add(ONE);
        observe(name + ".quotient", qr[0], null, step);
        return qr[0];
    }

    private static BigInteger roundEvenForConversion(BigInteger numerator, BigInteger denominator,
            String name, Tracker tracker) {
        if (numerator.signum() < 0 || denominator.signum() <= 0) throw new AssertionError("bad conversion ratio");
        observe(name + ".numerator", numerator, tracker, 0);
        observe(name + ".denominator", denominator, tracker, 0);
        BigInteger[] qr = numerator.divideAndRemainder(denominator);
        BigInteger twiceRemainder = qr[1].shiftLeft(1);
        observe(name + ".twice-remainder", twiceRemainder, tracker, 0);
        int cmp = twiceRemainder.compareTo(denominator);
        if (cmp > 0 || (cmp == 0 && qr[0].testBit(0))) qr[0] = qr[0].add(ONE);
        observe(name + ".quotient", qr[0], tracker, 0);
        return qr[0];
    }

    private static BigInteger mulQ(BigInteger a, BigInteger b, String name, int step) {
        BigInteger product = a.multiply(b);
        observe(name + ".product", product, null, step);
        return roundEven(product, Q, name + ".divide-q", step);
    }

    /** Exact Q120 conversion for every supported normal input above 2^-27. */
    private static BigInteger positiveInputQ(long absBits) {
        int exponent = (int) ((absBits >>> 52) & 0x7ffL);
        long fraction = absBits & 0x000fffffffffffffL;
        if (exponent == 0 || exponent == 0x7ff) throw new AssertionError("expected normal finite input");
        int shift = exponent - 955; // (53-bit significand * 2^(e-52)) * 2^120
        if (shift < 0) throw new AssertionError("input is not exactly representable at Q120");
        BigInteger significand = ONE.shiftLeft(52).add(BigInteger.valueOf(fraction));
        BigInteger result = significand.shiftLeft(shift);
        observe("input-q", result, null, 0);
        return result;
    }

    /** Returns sums after term indices 32, 64, and 128; each recurrence division is ties-to-even. */
    private static BigInteger[] asinSeries(BigInteger xQ) {
        if (xQ.signum() < 0 || xQ.compareTo(HALF_Q) > 0) throw new AssertionError("series domain not [0,1/2]");
        seriesCalls++;
        BigInteger term = xQ;
        BigInteger sum = term;
        observe("series-term", term, null, 0);
        observe("series-sum", sum, null, 0);
        BigInteger[] snapshots = new BigInteger[3];
        for (int n = 1; n <= 128; n++) {
            BigInteger firstPower = mulQ(term, xQ, "series-power-1", n);
            BigInteger secondPower = mulQ(firstPower, xQ, "series-power-2", n);
            long odd = 2L * n - 1L;
            BigInteger numerator = BigInteger.valueOf(odd * odd);
            BigInteger denominator = BigInteger.valueOf(2L * n * (2L * n + 1L));
            BigInteger scaled = secondPower.multiply(numerator);
            observe("series-ratio-product", scaled, null, n);
            term = roundEven(scaled, denominator, "series-ratio", n);
            sum = sum.add(term);
            observe("series-term", term, null, n);
            observe("series-sum", sum, null, n);
            recurrenceUpdates++;
            if (n == 32) snapshots[0] = sum;
            if (n == 64) snapshots[1] = sum;
            if (n == 128) snapshots[2] = sum;
        }
        return snapshots;
    }

    /** Newton square root plus exact correction, returning floor(sqrt(n)). */
    private static BigInteger sqrtFloor(BigInteger n) {
        if (n.signum() < 0) throw new AssertionError("negative radicand");
        if (n.signum() == 0) return BigInteger.ZERO;
        BigInteger x = ONE.shiftLeft((n.bitLength() + 1) / 2);
        observe("sqrt-iterate", x, null, 0);
        while (true) {
            BigInteger quotient = n.divide(x);
            BigInteger y = x.add(quotient).shiftRight(1);
            observe("sqrt-newton-sum", x.add(quotient), null, 0);
            observe("sqrt-iterate", y, null, 0);
            if (y.compareTo(x) >= 0) break;
            x = y;
        }
        BigInteger square = x.multiply(x);
        observe("sqrt-square", square, null, 0);
        while (square.compareTo(n) > 0) {
            x = x.subtract(ONE);
            square = x.multiply(x);
            observe("sqrt-square", square, null, 0);
        }
        while (true) {
            BigInteger next = x.add(ONE);
            BigInteger nextSquare = next.multiply(next);
            observe("sqrt-next-square", nextSquare, null, 0);
            if (nextSquare.compareTo(n) > 0) break;
            x = next;
            square = nextSquare;
        }
        BigInteger nextSquare = x.add(ONE).multiply(x.add(ONE));
        observe("sqrt-radicand", n, null, 0);
        observe("sqrt-square", square, null, 0);
        observe("sqrt-next-square", nextSquare, null, 0);
        if (square.compareTo(n) > 0 || nextSquare.compareTo(n) <= 0) throw new AssertionError("sqrt floor invariant");
        return x;
    }

    /** Correctly rounded nearest-even conversion of a nonnegative Q120 integer to binary64. */
    private static long qToDoubleBits(BigInteger magnitudeQ, Tracker tracker) {
        if (magnitudeQ.signum() < 0) throw new AssertionError("negative magnitude");
        if (magnitudeQ.signum() == 0) return 0L;
        int bitLength = magnitudeQ.bitLength();
        int exponent = bitLength - 1 - Q_BITS;
        int discarded = bitLength - 53;
        BigInteger significand;
        if (discarded > 0) {
            significand = roundEvenForConversion(magnitudeQ, ONE.shiftLeft(discarded), "binary64-significand", tracker);
        } else {
            significand = magnitudeQ.shiftLeft(-discarded);
            observe("binary64-significand", significand, tracker, 0);
        }
        if (significand.bitLength() > 53) { significand = significand.shiftRight(1); exponent++; }
        if (exponent < -1022 || exponent > 1023 || significand.bitLength() != 53) {
            throw new AssertionError("unexpected Q120 output range");
        }
        BigInteger fraction = significand.subtract(ONE.shiftLeft(52));
        if (fraction.signum() < 0 || fraction.bitLength() > 52) throw new AssertionError("invalid binary64 fraction");
        observe("binary64-result-significand", significand, tracker, 0);
        return ((long) (exponent + 1023) << 52) | fraction.longValue();
    }

    private static long[] positiveAsin(long absBits) {
        if (absBits == 0L || absBits <= TINY_BITS) return new long[] {absBits, absBits, absBits};
        BigInteger xQ = positiveInputQ(absBits);
        BigInteger[] sums = null;
        BigInteger endpointDelta = null;
        BigInteger yQ = null;
        BigInteger rootQ = null;
        boolean reduced = absBits > HALF_BITS && absBits < ONE_BITS;
        if (absBits <= HALF_BITS) {
            sums = asinSeries(xQ);
        } else if (absBits == ONE_BITS) {
            // Exact real pi/2 rounded to the nearest Q120 integer.
            for (Tracker tracker : TRACKERS) observe("pi-over-two-q", PI_OVER_2_Q, tracker, 0);
        } else {
            endpointDelta = Q.subtract(xQ);
            observe("endpoint-delta", endpointDelta, null, 0);
            yQ = roundEven(endpointDelta, TWO, "half-endpoint-delta", 0);
            BigInteger radicand = yQ.multiply(Q);
            observe("sqrt-radicand", radicand, null, 0);
            rootQ = sqrtFloor(radicand);
            observe("sqrt-q", rootQ, null, 0);
            sums = asinSeries(rootQ);
        }

        long[] values = new long[3];
        for (int i = 0; i < LIMITS.length; i++) {
            BigInteger resultQ;
            if (absBits == ONE_BITS) {
                resultQ = PI_OVER_2_Q;
            } else if (reduced) {
                resultQ = PI_OVER_2_Q.subtract(sums[i].shiftLeft(1));
            } else {
                resultQ = sums[i];
            }
            observe("asin-result-q", resultQ, TRACKERS[i], 0);
            values[i] = qToDoubleBits(resultQ, TRACKERS[i]);
        }
        kernelEvaluations++;
        return values;
    }

    private static long[] candidate(long inputBits) {
        long absBits = inputBits & Long.MAX_VALUE;
        Long key = Long.valueOf(absBits);
        long[] positive = POSITIVE_CACHE.get(key);
        if (positive == null) {
            positive = positiveAsin(absBits);
            POSITIVE_CACHE.put(key, positive);
        }
        long[] signed = new long[3];
        long sign = inputBits & Long.MIN_VALUE;
        for (int i = 0; i < 3; i++) signed[i] = positive[i] | sign;
        return signed;
    }

    private static long ordered(long bits) { return bits < 0 ? ~bits : bits ^ Long.MIN_VALUE; }
    private static int orderedFloat(int bits) { return bits < 0 ? ~bits : bits ^ 0x80000000; }
    private static BigInteger unsigned(long value) {
        BigInteger low = BigInteger.valueOf(value & Long.MAX_VALUE);
        return value < 0 ? low.setBit(63) : low;
    }
    private static BigInteger ulpDistance(long a, long b) {
        return unsigned(ordered(a)).subtract(unsigned(ordered(b))).abs();
    }
    private static String hex64(long value) { return String.format(Locale.ROOT, "%016x", Long.valueOf(value)); }
    private static String hex32(int value) { return String.format(Locale.ROOT, "%08x", Integer.valueOf(value)); }
    private static long parseHex64(String value) { return Long.parseUnsignedLong(value, 16); }
    private static int parseHex32(String value) { return (int) Long.parseLong(value, 16); }

    private static final class Results {
        long supported, refused, doubleMismatch, floatMismatch, monotonicDouble, monotonicFloat;
        BigInteger maxUlp = BigInteger.ZERO;
        String worstInput = "0000000000000000";
    }

    private static final class VariantDifference {
        long different;
        BigInteger maxUlp = BigInteger.ZERO;
        String worstInput = "0000000000000000";
    }

    private static VariantDifference[] compareVariants(List<Sample> samples) {
        VariantDifference[] differences = {new VariantDifference(), new VariantDifference()};
        for (Sample sample : samples) {
            if (!sample.supported) continue;
            for (int i = 0; i < differences.length; i++) {
                long left = sample.actual[i];
                long right = sample.actual[i + 1];
                BigInteger distance = ulpDistance(left, right);
                if (distance.signum() != 0) differences[i].different++;
                if (distance.compareTo(differences[i].maxUlp) > 0) {
                    differences[i].maxUlp = distance;
                    differences[i].worstInput = hex64(sample.input);
                }
            }
        }
        return differences;
    }

    private static List<Sample> readSamples(File oracle) throws Exception {
        List<Sample> samples = new ArrayList<Sample>();
        BufferedReader reader = new BufferedReader(new InputStreamReader(new FileInputStream(oracle), "UTF-8"));
        try {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.length() == 0 || line.charAt(0) == '#' || line.startsWith("categories\t")) continue;
                String[] fields = line.split("\t", -1);
                if (fields.length != 5) throw new AssertionError("malformed oracle row: " + line);
                boolean supported = "SUPPORTED".equals(fields[2]);
                if (!supported && !"REFUSE".equals(fields[2])) throw new AssertionError("unknown policy " + fields[2]);
                if (supported) {
                    samples.add(new Sample(fields[0], parseHex64(fields[1]), true,
                            parseHex64(fields[3]), parseHex32(fields[4])));
                } else {
                    if (!"-".equals(fields[3]) || !"-".equals(fields[4])) throw new AssertionError("refused row has oracle result");
                    samples.add(new Sample(fields[0], parseHex64(fields[1]), false, 0L, 0));
                }
            }
        } finally { reader.close(); }
        return samples;
    }

    private static Results[] compare(List<Sample> samples, File mismatchFile) throws Exception {
        Results[] all = {new Results(), new Results(), new Results()};
        Collections.sort(samples, new Comparator<Sample>() {
            public int compare(Sample a, Sample b) { return Long.compareUnsigned(ordered(a.input), ordered(b.input)); }
        });
        BufferedWriter bad = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(mismatchFile), "UTF-8"));
        try {
            bad.write("iterations\tcategories\tinput_bits\texpected_asin_bits\tactual_asin_bits\tulp_distance\texpected_float_bits\tactual_float_bits\n");
            measure = true;
            for (Sample sample : samples) {
                if (!sample.supported) {
                    for (Results result : all) result.refused++;
                    long absBits = sample.input & Long.MAX_VALUE;
                    boolean exponentAllOnes = (absBits & 0x7ff0000000000000L) == 0x7ff0000000000000L;
                    if (!exponentAllOnes && absBits <= ONE_BITS) {
                        throw new AssertionError("oracle refused an in-domain finite input " + hex64(sample.input));
                    }
                    continue;
                }
                long[] actual = candidate(sample.input);
                sample.actual = actual;
                for (int i = 0; i < 3; i++) {
                    Results result = all[i];
                    result.supported++;
                    int actualFloat = Float.floatToRawIntBits((float) Double.longBitsToDouble(actual[i]));
                    BigInteger distance = ulpDistance(sample.expected, actual[i]);
                    if (distance.compareTo(result.maxUlp) > 0) {
                        result.maxUlp = distance;
                        result.worstInput = hex64(sample.input);
                    }
                    boolean doubleBad = sample.expected != actual[i];
                    boolean floatBad = sample.expectedFloat != actualFloat;
                    if (doubleBad) result.doubleMismatch++;
                    if (floatBad) result.floatMismatch++;
                    if (doubleBad || floatBad) {
                        bad.write(LIMITS[i] + "\t" + sample.categories + "\t" + hex64(sample.input)
                                + "\t" + hex64(sample.expected) + "\t" + hex64(actual[i])
                                + "\t" + distance.toString() + "\t" + hex32(sample.expectedFloat)
                                + "\t" + hex32(actualFloat) + "\n");
                    }
                }
            }
        } finally { measure = false; bad.close(); }

        for (int i = 0; i < 3; i++) {
            long previousDouble = 0L;
            int previousFloat = 0;
            boolean havePrevious = false;
            for (Sample sample : samples) {
                if (!sample.supported) continue;
                long bits = sample.actual[i];
                int fbits = Float.floatToRawIntBits((float) Double.longBitsToDouble(bits));
                if (havePrevious) {
                    if (Long.compareUnsigned(ordered(bits), ordered(previousDouble)) < 0) all[i].monotonicDouble++;
                    if (Integer.compareUnsigned(orderedFloat(fbits), orderedFloat(previousFloat)) < 0) all[i].monotonicFloat++;
                }
                previousDouble = bits;
                previousFloat = fbits;
                havePrevious = true;
            }
        }
        return new Results[] {all[0], all[1], all[2]};
    }

    private static BigDecimal exactDecimal(long positiveBits) {
        return new BigDecimal(Double.longBitsToDouble(positiveBits));
    }

    /** Exact-rational nearest-even check used only to validate the integer converter. */
    private static boolean independentlyNearest(BigInteger n, long candidateBits) {
        BigDecimal target = new BigDecimal(n).divide(new BigDecimal(Q));
        BigDecimal candidate = exactDecimal(candidateBits);
        int side = target.compareTo(candidate);
        if (side == 0) return true;
        long lowBits, highBits;
        if (side > 0) { lowBits = candidateBits; highBits = candidateBits + 1L; }
        else {
            if (candidateBits == 0L) return false;
            lowBits = candidateBits - 1L;
            highBits = candidateBits;
        }
        BigDecimal midpoint = exactDecimal(lowBits).add(exactDecimal(highBits)).divide(BigDecimal.valueOf(2L));
        int midpointSide = target.compareTo(midpoint);
        if (midpointSide < 0) return candidateBits == lowBits;
        if (midpointSide > 0) return candidateBits == highBits;
        return (candidateBits & 1L) == 0L;
    }

    private static void verifyPi() {
        String pi = "3.14159265358979323846264338327950288419716939937510582097494459230781640628620899862803482534211706798214808651328230664709384460955058223172535940812848111745028410270193852110555964462294895493038196";
        BigInteger rounded = new BigDecimal(pi).multiply(new BigDecimal(Q)).divide(BigDecimal.valueOf(2L))
                .setScale(0, BigDecimal.ROUND_HALF_EVEN).toBigIntegerExact();
        if (!rounded.equals(PI_OVER_2_Q)) throw new AssertionError("pi/2 Q120 scalar validation failed");
    }

    private static void verifySqrt() {
        boolean previousMeasure = measure;
        measure = false;
        Random random = new Random(0x5351525431323043L);
        for (int i = 0; i < 4096; i++) {
            BigInteger n = new BigInteger(240, random);
            BigInteger root = sqrtFloor(n);
            if (root.multiply(root).compareTo(n) > 0 || root.add(ONE).multiply(root.add(ONE)).compareTo(n) <= 0) {
                throw new AssertionError("sqrt control failed at " + n.toString(16));
            }
        }
        measure = previousMeasure;
    }

    private static long qToDoubleUnmeasured(BigInteger n) {
        return qToDoubleBits(n, null);
    }

    private static long verifyConversion() {
        boolean previousMeasure = measure;
        measure = false;
        Random random = new Random(0x5142494e36344356L);
        BigInteger[] named = {
            BigInteger.ZERO, ONE, TWO, Q.shiftRight(1), Q.subtract(ONE), Q, Q.add(ONE),
            Q.shiftLeft(1).subtract(ONE), Q.shiftLeft(1), PI_OVER_2_Q,
            Q.add(ONE.shiftLeft(67)), Q.add(ONE.shiftLeft(67).multiply(BigInteger.valueOf(3L))),
            Q.subtract(ONE.shiftLeft(67)), Q.subtract(ONE.shiftLeft(67).multiply(BigInteger.valueOf(3L)))
        };
        long checks = 0;
        for (BigInteger n : named) {
            if (!independentlyNearest(n, qToDoubleUnmeasured(n))) throw new AssertionError("named conversion mismatch");
            checks++;
        }
        for (int i = 0; i < 4096; i++) {
            BigInteger n = new BigInteger(121, random);
            if (!independentlyNearest(n, qToDoubleUnmeasured(n))) throw new AssertionError("random conversion mismatch");
            checks++;
        }
        measure = previousMeasure;
        return checks;
    }

    private static String sha256(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        FileInputStream in = new FileInputStream(file);
        try {
            byte[] buffer = new byte[32768];
            int count;
            while ((count = in.read(buffer)) >= 0) if (count != 0) digest.update(buffer, 0, count);
        } finally { in.close(); }
        StringBuilder out = new StringBuilder();
        for (byte b : digest.digest()) out.append(String.format(Locale.ROOT, "%02x", b & 255));
        return out.toString();
    }

    private static String escape(String s) { return s.replace("\\", "\\\\").replace("\"", "\\\""); }

    private static void writeSummary(File file, Results[] results, VariantDifference[] differences,
            long sampleCount, long conversionChecks, File oracle) throws Exception {
        BufferedWriter out = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(file), "UTF-8"));
        try {
            out.write("{\n  \"algorithm\": \"test-only Q120 nearest-even recurrence; exact integer floor sqrt; pi/2 Q120 scalar\",\n");
            out.write("  \"oracle_rows\": " + sampleCount + ",\n");
            out.write("  \"unique_absolute_kernel_evaluations\": " + kernelEvaluations + ",\n");
            out.write("  \"series_calls\": " + seriesCalls + ",\n");
            out.write("  \"recurrence_updates\": " + recurrenceUpdates + ",\n");
            out.write("  \"integer_sqrt_control_checks\": 4096,\n");
            out.write("  \"q120_to_binary64_exact_nearest_checks\": " + conversionChecks + ",\n");
            out.write("  \"positive_series_tail_bound\": \"for sum through t_N, 0<=z<=1/2: omitted positive tail <= 1/(3*2^(2N+1)); endpoint-reduced asin result doubles this bound\",\n");
            out.write("  \"tail_bounds_by_iteration\": [{\"N\":32,\"series\":\"1/(3*2^65)\",\"endpoint_reduced_result\":\"1/(3*2^64)\"},{\"N\":64,\"series\":\"1/(3*2^129)\",\"endpoint_reduced_result\":\"1/(3*2^128)\"},{\"N\":128,\"series\":\"1/(3*2^257)\",\"endpoint_reduced_result\":\"1/(3*2^256)\"}],\n");
            out.write("  \"iteration_results\": [\n");
            for (int i = 0; i < results.length; i++) {
                Results r = results[i];
                Tracker t = TRACKERS[i];
                out.write("    {\"N\": " + LIMITS[i] + ", \"supported\": " + r.supported
                        + ", \"refused\": " + r.refused
                        + ", \"double_raw_mismatches\": " + r.doubleMismatch
                        + ", \"float_cast_raw_mismatches\": " + r.floatMismatch
                        + ", \"sampled_double_monotonicity_violations\": " + r.monotonicDouble
                        + ", \"sampled_float_monotonicity_violations\": " + r.monotonicFloat
                        + ", \"maximum_ulp_distance\": \"" + r.maxUlp
                        + "\", \"worst_input_bits\": \"" + r.worstInput
                        + "\", \"max_intermediate_abs_bit_length\": " + t.maxBits
                        + ", \"max_intermediate_operation\": \"" + escape(t.maxOperation)
                        + "\", \"intermediate_bit_lengths_by_operation\": {");
                int j = 0;
                for (Map.Entry<String, Integer> entry : t.bitsByOperation.entrySet()) {
                    out.write((j++ == 0 ? "" : ",") + "\n      \"" + escape(entry.getKey()) + "\": " + entry.getValue());
                }
                out.write("\n    }}" + (i + 1 == results.length ? "\n" : ",\n"));
            }
            out.write("  ],\n");
            out.write("  \"iteration_variant_differences\": [");
            for (int i = 0; i < differences.length; i++) {
                VariantDifference d = differences[i];
                out.write((i == 0 ? "" : ",") + "{\"from_N\":" + LIMITS[i]
                        + ",\"to_N\":" + LIMITS[i + 1] + ",\"different_double_rows\":" + d.different
                        + ",\"maximum_ulp_distance\":\"" + d.maxUlp
                        + "\",\"worst_input_bits\":\"" + d.worstInput + "\"}");
            }
            out.write("],\n");
            out.write("  \"signed_256_bound\": \"all tracked candidate intermediates satisfy abs(value)<2^255\",\n");
            out.write("  \"oracle_sha256\": \"" + sha256(oracle) + "\",\n");
            out.write("  \"interpretation\": \"generated OpenJDK 8 comparison only; no universal correctness or Minecraft/EVM behavior claim\"\n}\n");
        } finally { out.close(); }
    }

    private static void writeRunSummary(File file, Results[] results, VariantDifference[] differences,
            long samples, long conversionChecks) throws Exception {
        BufferedWriter out = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(file), "UTF-8"));
        try {
            out.write("oracle_rows=" + samples + "\n");
            out.write("unique_absolute_kernel_evaluations=" + kernelEvaluations + "\n");
            out.write("series_calls=" + seriesCalls + " recurrence_updates=" + recurrenceUpdates + "\n");
            out.write("integer_sqrt_control_checks=4096 q120_to_binary64_exact_nearest_checks=" + conversionChecks + "\n");
            out.write("tail_bounds: N32=1/(3*2^65), endpoint-result<=1/(3*2^64); N64=1/(3*2^129), endpoint-result<=1/(3*2^128); N128=1/(3*2^257), endpoint-result<=1/(3*2^256)\n");
            for (int i = 0; i < results.length; i++) {
                Results r = results[i];
                Tracker t = TRACKERS[i];
                out.write("N=" + LIMITS[i] + " supported=" + r.supported + " refused=" + r.refused
                        + " double_raw_mismatches=" + r.doubleMismatch
                        + " float_cast_raw_mismatches=" + r.floatMismatch
                        + " max_ulp=" + r.maxUlp + " at=0x" + r.worstInput
                        + " monotonic_violations(double,float)=" + r.monotonicDouble + "," + r.monotonicFloat
                        + " max_intermediate_bits=" + t.maxBits + " at=" + t.maxOperation + "\n");
            }
            for (int i = 0; i < differences.length; i++) {
                VariantDifference d = differences[i];
                out.write("variant_N=" + LIMITS[i] + "_to_" + LIMITS[i + 1]
                        + " different_rows=" + d.different + " max_ulp=" + d.maxUlp
                        + " at=0x" + d.worstInput + "\n");
            }
        } finally { out.close(); }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 4) throw new IllegalArgumentException("usage: Q120AsinCoverageProbe ORACLE.tsv MISMATCHES.tsv SUMMARY.json RUN.txt");
        verifyPi();
        verifySqrt();
        long conversionChecks = verifyConversion();
        List<Sample> samples = readSamples(new File(args[0]));
        Results[] results = compare(samples, new File(args[1]));
        VariantDifference[] differences = compareVariants(samples);
        writeSummary(new File(args[2]), results, differences, samples.size(), conversionChecks, new File(args[0]));
        writeRunSummary(new File(args[3]), results, differences, samples.size(), conversionChecks);
        for (int i = 0; i < results.length; i++) {
            Results r = results[i];
            System.out.println("N=" + LIMITS[i] + " supported=" + r.supported + " refused=" + r.refused
                    + " double_mismatches=" + r.doubleMismatch + " float_mismatches=" + r.floatMismatch
                    + " max_ulp=" + r.maxUlp + " monotonic=" + r.monotonicDouble + "/" + r.monotonicFloat
                    + " max_bits=" + TRACKERS[i].maxBits);
        }
    }
}
