import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.Set;

/** Generated-input OpenJDK 8 oracle only. Never part of guest execution. */
public strictfp final class AsinJava8HostOracle {
    private static final long RANDOM_SEED = 0x4153494e51313230L;
    private static final int RANDOM_MAGNITUDES = 4096;

    private static final class Probe {
        final long bits;
        final Set<String> categories = new LinkedHashSet<String>();
        Probe(long bits) { this.bits = bits; }
    }

    private static final Map<Long, Probe> PROBES = new LinkedHashMap<Long, Probe>();

    private static void add(long bits, String category) {
        Long key = Long.valueOf(bits);
        Probe probe = PROBES.get(key);
        if (probe == null) {
            probe = new Probe(bits);
            PROBES.put(key, probe);
        }
        probe.categories.add(category);
    }

    private static long raw(double value) {
        return Double.doubleToRawLongBits(value);
    }

    private static String hex(long value) {
        return String.format(Locale.ROOT, "%016x", Long.valueOf(value));
    }

    private static String sha256(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] buffer = new byte[32768];
        java.io.FileInputStream in = new java.io.FileInputStream(file);
        try {
            int count;
            while ((count = in.read(buffer)) >= 0) {
                if (count != 0) digest.update(buffer, 0, count);
            }
        } finally {
            in.close();
        }
        StringBuilder result = new StringBuilder();
        for (byte b : digest.digest()) result.append(String.format(Locale.ROOT, "%02x", b & 255));
        return result.toString();
    }

    private static void generate() {
        for (int k = 0; k <= 256; k++) {
            double x = k / 256.0;
            add(raw(x), "grid-k256");
            add(raw(-x), "grid-negative-mirror");
        }

        // Consecutive binary64 values inward from both closed endpoints.
        long positiveOne = 0x3ff0000000000000L;
        long negativeOne = 0xbff0000000000000L;
        for (int i = 0; i <= 64; i++) {
            add(positiveOne - i, "near-positive-endpoint");
            add(negativeOne - i, "near-negative-endpoint");
        }

        // Values immediately around 1/2 and the rigorously-return-input cutoff 2^-27.
        long half = 0x3fe0000000000000L;
        long cutoff = 0x3e40000000000000L;
        for (int i = -4; i <= 4; i++) {
            add(half + i, "near-half-boundary");
            add(half - i, "near-half-boundary-negative-magnitude");
            add(cutoff + i, "near-tiny-cutoff");
            add(cutoff - i, "near-tiny-cutoff");
            add(0xbe40000000000000L - i, "near-negative-tiny-cutoff");
            add(0xbe40000000000000L + i, "near-negative-tiny-cutoff");
        }

        long[] tiny = {
            0L, 0x8000000000000000L,
            1L, 2L, 3L, 0x000fffffffffffffL, 0x0010000000000000L,
            0x0010000000000001L, 0x3c90000000000000L, 0xbc90000000000000L,
            0x3e3fffffffffffffL, 0xbe3fffffffffffffL,
            0x3e40000000000000L, 0xbe40000000000000L
        };
        for (long bits : tiny) {
            add(bits, "tiny-subnormal-normal-signed-zero");
            add(bits ^ Long.MIN_VALUE, "tiny-negative-mirror");
        }

        Random random = new Random(RANDOM_SEED);
        for (int i = 0; i < RANDOM_MAGNITUDES; i++) {
            double uniform = random.nextDouble();
            long uniformBits = raw(uniform);
            add(uniformBits, "random-uniform-magnitude");
            add(uniformBits ^ Long.MIN_VALUE, "random-uniform-negative");

            // Exponent-stratified finite magnitudes in [0,1), including subnormals.
            int exponent = random.nextInt(1023);
            long fraction = random.nextLong() & 0x000fffffffffffffL;
            long stratified = ((long) exponent << 52) | fraction;
            add(stratified, "random-exponent-stratified");
            add(stratified ^ Long.MIN_VALUE, "random-exponent-stratified-negative");
        }

        // Unsupported/refused controls: intentionally no Math.asin call is made for these.
        add(0x3ff0000000000001L, "refuse-finite-out-of-range");
        add(0xbff0000000000001L, "refuse-finite-out-of-range");
        add(0x4000000000000000L, "refuse-finite-out-of-range");
        add(0xc000000000000000L, "refuse-finite-out-of-range");
        add(0x7fefffffffffffffL, "refuse-finite-out-of-range");
        add(0xffefffffffffffffL, "refuse-finite-out-of-range");
        add(0x7ff0000000000000L, "refuse-infinity-or-nan");
        add(0xfff0000000000000L, "refuse-infinity-or-nan");
        add(0x7ff8000000000001L, "refuse-infinity-or-nan");
        add(0xfff8000000000001L, "refuse-infinity-or-nan");
        add(0x7ff0000000000001L, "refuse-infinity-or-nan");
    }

    private static String categories(Probe probe) {
        StringBuilder out = new StringBuilder();
        for (String category : probe.categories) {
            if (out.length() != 0) out.append(',');
            out.append(category);
        }
        return out.toString();
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("usage: AsinJava8HostOracle OUT.tsv");
        generate();
        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null && !parent.isDirectory() && !parent.mkdirs()) {
            throw new IllegalStateException("cannot create " + parent);
        }

        int supported = 0;
        int refused = 0;
        BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(
                new FileOutputStream(output), "UTF-8"));
        try {
            writer.write("# generated OpenJDK 8 oracle; inputs are raw binary64; refused rows have no oracle value\n");
            writer.write("categories\tinput_bits\tpolicy\tasin_bits\tfloat_bits\n");
            for (Probe probe : PROBES.values()) {
                long bits = probe.bits;
                double x = Double.longBitsToDouble(bits);
                boolean finite = (bits & 0x7ff0000000000000L) != 0x7ff0000000000000L;
                boolean inRange = finite && Math.abs(x) <= 1.0;
                writer.write(categories(probe));
                writer.write('\t');
                writer.write(hex(bits));
                if (inRange) {
                    double y = Math.asin(x);
                    int f = Float.floatToRawIntBits((float) y);
                    writer.write("\tSUPPORTED\t");
                    writer.write(hex(Double.doubleToRawLongBits(y)));
                    writer.write('\t');
                    writer.write(String.format(Locale.ROOT, "%08x", Integer.valueOf(f)));
                    supported++;
                } else {
                    writer.write("\tREFUSE\t-\t-");
                    refused++;
                }
                writer.write('\n');
            }
        } finally {
            writer.close();
        }

        File summary = new File(output.getParentFile(), "oracle-summary.txt");
        BufferedWriter report = new BufferedWriter(new OutputStreamWriter(
                new FileOutputStream(summary), "UTF-8"));
        try {
            report.write("oracle=java.lang.Math.asin(double), evaluated only for supported generated inputs\n");
            report.write("java.version=" + System.getProperty("java.version") + "\n");
            report.write("java.vm.name=" + System.getProperty("java.vm.name") + "\n");
            report.write("strictfp=true\n");
            report.write("random.seed=0x" + Long.toHexString(RANDOM_SEED) + "\n");
            report.write("random.magnitudes=" + RANDOM_MAGNITUDES + " (uniform plus exponent-stratified, each with sign mirror)\n");
            report.write("unique.rows=" + PROBES.size() + "\n");
            report.write("supported.rows=" + supported + "\n");
            report.write("refused.controls=" + refused + "\n");
            report.write("samples.tsv.sha256=" + sha256(output) + "\n");
            report.write("range-policy=finite raw binary64 x with |x|<=1 only; NaN, infinities, and finite |x|>1 are REFUSE controls; no Math.asin value is evaluated for controls\n");
        } finally {
            report.close();
        }
    }
}
