import java.io.BufferedWriter;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.TreeMap;

/** Generated-only OpenJDK 8 Math.asin oracle. Never part of guest execution. */
public strictfp final class AsinCoverageJava8Oracle {
    private static final long RANDOM_SEED = 0x4153494e36353535L;
    private static final int RANDOM_MAGNITUDES = 4096;
    private static final long ONE_BITS = 0x3ff0000000000000L;

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

    private static long raw(double value) { return Double.doubleToRawLongBits(value); }

    private static String hex64(long value) {
        return String.format(Locale.ROOT, "%016x", Long.valueOf(value));
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

    private static void mirrored(long positiveBits, String category) {
        add(positiveBits, category);
        add(positiveBits ^ Long.MIN_VALUE, category + "-neg");
    }

    private static void generate() {
        // Full dense rational grid, with both signs and both signed zeros.
        for (int k = 0; k <= 65535; k++) {
            double x = k / 65535.0;
            mirrored(raw(x), "grid65535");
        }

        // Consecutive binary64 neighbors inward from |x|=1, plus geometric approaches.
        for (int i = 0; i <= 256; i++) mirrored(ONE_BITS - i, "near1-ulp");
        for (int exponent = 1; exponent <= 52; exponent++) {
            double x = 1.0 - Math.scalb(1.0, -exponent);
            mirrored(raw(x), "near1-pow2");
        }

        // Around the series/endpoint-reduction seam and the proven tiny passthrough seam.
        long half = 0x3fe0000000000000L;
        long tiny = 0x3e40000000000000L; // 2^-27
        for (int i = -64; i <= 64; i++) {
            mirrored(half + i, "near-half");
            mirrored(tiny + i, "near-tiny");
        }
        long[] edgeBits = {
            0L, 1L, 2L, 3L, 0x000fffffffffffffL, 0x0010000000000000L,
            0x0010000000000001L, 0x3c90000000000000L, 0x3e3fffffffffffffL,
            0x3e40000000000000L, 0x3fefffffffffffffL, ONE_BITS
        };
        for (long bits : edgeBits) mirrored(bits, "zero-subnormal-normal-edge");

        // Deterministic finite magnitudes in [0,1), both uniform and exponent-stratified.
        Random random = new Random(RANDOM_SEED);
        for (int i = 0; i < RANDOM_MAGNITUDES; i++) {
            mirrored(raw(random.nextDouble()), "random-uniform");
            int exponent = random.nextInt(1023); // raw exponent 0..1022, hence finite |x|<1
            long fraction = random.nextLong() & 0x000fffffffffffffL;
            long stratified = ((long) exponent << 52) | fraction;
            mirrored(stratified, "random-exponent");
        }

        // Out-of-domain/nonfinite policy controls; deliberately no Math.asin evaluation.
        long[] refused = {
            0x3ff0000000000001L, 0xbff0000000000001L,
            0x4000000000000000L, 0xc000000000000000L,
            0x7fefffffffffffffL, 0xffefffffffffffffL,
            0x7ff0000000000000L, 0xfff0000000000000L,
            0x7ff8000000000001L, 0xfff8000000000001L,
            0x7ff0000000000001L
        };
        for (long bits : refused) add(bits, "refuse-control");
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
        if (args.length != 1) throw new IllegalArgumentException("usage: AsinCoverageJava8Oracle OUT.tsv");
        generate();
        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null && !parent.isDirectory() && !parent.mkdirs()) {
            throw new IllegalStateException("cannot create " + parent);
        }

        long supported = 0, refused = 0;
        Map<String, Long> categoryRows = new TreeMap<String, Long>();
        BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(
                new FileOutputStream(output), "UTF-8"));
        try {
            writer.write("# generated OpenJDK 8 oracle; refused rows have no oracle value\n");
            writer.write("categories\tinput_bits\tpolicy\tasin_bits\tfloat_bits\n");
            for (Probe probe : PROBES.values()) {
                String cats = categories(probe);
                for (String category : probe.categories) {
                    Long previous = categoryRows.get(category);
                    categoryRows.put(category, Long.valueOf(previous == null ? 1 : previous.longValue() + 1));
                }
                long bits = probe.bits;
                long exponent = bits & 0x7ff0000000000000L;
                boolean finite = exponent != 0x7ff0000000000000L;
                boolean inRange = finite && (bits & Long.MAX_VALUE) <= ONE_BITS;
                writer.write(cats);
                writer.write('\t');
                writer.write(hex64(bits));
                if (inRange) {
                    double y = Math.asin(Double.longBitsToDouble(bits));
                    int f = Float.floatToRawIntBits((float) y);
                    writer.write("\tSUPPORTED\t");
                    writer.write(hex64(Double.doubleToRawLongBits(y)));
                    writer.write('\t');
                    writer.write(String.format(Locale.ROOT, "%08x", Integer.valueOf(f)));
                    supported++;
                } else {
                    writer.write("\tREFUSE\t-\t-");
                    refused++;
                }
                writer.write('\n');
            }
        } finally { writer.close(); }

        File summary = new File(output.getParentFile(), "oracle-summary.txt");
        BufferedWriter report = new BufferedWriter(new OutputStreamWriter(
                new FileOutputStream(summary), "UTF-8"));
        try {
            report.write("oracle=java.lang.Math.asin(double), generated inputs only\n");
            report.write("java.version=" + System.getProperty("java.version") + "\n");
            report.write("java.vm.name=" + System.getProperty("java.vm.name") + "\n");
            report.write("java.vendor=" + System.getProperty("java.vendor") + "\n");
            report.write("strictfp=true\n");
            report.write("random.seed=0x" + Long.toHexString(RANDOM_SEED) + "\n");
            report.write("random.magnitudes=" + RANDOM_MAGNITUDES + " per generator; uniform and exponent-stratified, each with sign mirror\n");
            report.write("unique.rows=" + PROBES.size() + "\n");
            report.write("supported.rows=" + supported + "\n");
            report.write("refused.controls=" + refused + " (Math.asin not called)\n");
            report.write("samples.tsv.sha256=" + sha256(output) + "\n");
            report.write("category.memberships (overlap is intentional):\n");
            for (Map.Entry<String, Long> entry : categoryRows.entrySet()) {
                report.write("  " + entry.getKey() + "=" + entry.getValue() + "\n");
            }
            report.write("range-policy=finite |x|<=1 only; all other controls are REFUSE without an oracle result\n");
            report.write("provenance=generated numerical controls only; known original Minecraft argument remains authenticated +0.0 only\n");
        } finally { report.close(); }
    }
}
