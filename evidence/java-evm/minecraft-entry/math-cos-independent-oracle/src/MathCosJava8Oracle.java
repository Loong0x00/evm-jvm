import java.io.BufferedWriter;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.Charset;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.Set;

/** Generated-input OpenJDK 8 Math.cos oracle only; never guest execution code. */
public strictfp final class MathCosJava8Oracle {
    private static final long SIGN = 0x8000000000000000L;
    private static final long ABS = 0x7fffffffffffffffL;
    private static final long BOUND_BITS = 0x401921fb54442d18L;
    private static final int GRID_SIZE = 65536;
    private static final int RANDOM_COUNT = 4096;
    private static final long RANDOM_SEED = 0x434f535131323030L;
    private static final Map<Long, Probe> PROBES = new LinkedHashMap<Long, Probe>();

    private static final class Probe {
        final long bits;
        final Set<String> categories = new LinkedHashSet<String>();
        Probe(long bits) { this.bits = bits; }
    }

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

    private static void addSigned(long positiveBits, String category) {
        add(positiveBits, category + ":+");
        add(positiveBits | SIGN, category + ":-");
    }

    private static void generate() {
        add(0x0000000000000000L, "signed-zero:+");
        add(0x8000000000000000L, "signed-zero:-");

        // This is a hypothetical generated grid, not evidence about later genuine inputs.
        for (int i = 0; i < GRID_SIZE; i++) {
            double x = (double) i * 6.283185307179586 / 65536;
            add(raw(x), "grid-2pi-over-65536:" + i);
        }

        // All in-domain dyadic points k/256 and their negative mirrors.
        for (int k = 1; k <= 1608; k++) {
            addSigned(raw(k / 256.0), "dyadic-k256:" + k);
        }

        // Immediate raw-bit neighborhoods of the binary64 pi/2, pi, and 2*pi constants.
        long[] centers = new long[] {
            0x3ff921fb54442d18L, 0x400921fb54442d18L, BOUND_BITS
        };
        String[] names = new String[] { "near-pi-over-2", "near-pi", "near-2pi" };
        for (int c = 0; c < centers.length; c++) {
            for (long delta = -32; delta <= 32; delta++) {
                long bits = centers[c] + delta;
                addSigned(bits, names[c] + ":raw-delta=" + delta);
            }
        }

        // Tiny values, including subnormal/normal boundaries and both signs.
        addSigned(0x0000000000000001L, "min-subnormal");
        addSigned(0x0000000000000002L, "second-subnormal");
        addSigned(0x000fffffffffffffL, "max-subnormal");
        addSigned(0x0010000000000000L, "min-normal");
        for (int exponent = 1; exponent <= 120; exponent++) {
            long bits = ((long) (1023 - exponent)) << 52;
            addSigned(bits, "power-of-two-minus-" + exponent);
        }
        long tinyCut = 0x3e40000000000000L; // 2^-27
        for (long delta = -4; delta <= 4; delta++) {
            addSigned(tinyCut + delta, "near-2^-27:raw-delta=" + delta);
        }

        // Explicit unsupported controls. The oracle must not call Math.cos on these.
        add(0x401921fb54442d19L, "refuse-next-after-domain-bound");
        add(0xc01921fb54442d19L, "refuse-negative-next-after-domain-bound");
        add(0x4020000000000000L, "refuse-positive-eight");
        add(0xc020000000000000L, "refuse-negative-eight");
        add(0x7fefffffffffffffL, "refuse-positive-max-finite");
        add(0xffefffffffffffffL, "refuse-negative-max-finite");
        add(0x7ff0000000000000L, "refuse-positive-infinity");
        add(0xfff0000000000000L, "refuse-negative-infinity");
        add(0x7ff8000000000001L, "refuse-positive-quiet-nan-payload-1");
        add(0xfff8000000000001L, "refuse-negative-quiet-nan-payload-1");
        add(0x7ff0000000000001L, "refuse-positive-signaling-nan-payload-1");
        add(0xfff0000000000001L, "refuse-negative-signaling-nan-payload-1");

        Random random = new Random(RANDOM_SEED);
        double bound = Double.longBitsToDouble(BOUND_BITS);
        for (int i = 0; i < RANDOM_COUNT; i++) {
            double magnitude = random.nextDouble() * bound;
            long bits = raw(magnitude) & ABS;
            addSigned(bits, "random-uniform-magnitude:" + i);
        }
    }

    private static boolean supported(long bits) {
        long magnitude = bits & ABS;
        long exponent = (magnitude >>> 52) & 0x7ffL;
        return exponent != 0x7ffL && magnitude <= BOUND_BITS;
    }

    private static String hex(long value, int digits) {
        String format = digits == 8 ? "%08x" : "%016x";
        return String.format(Locale.ROOT, format, Long.valueOf(value));
    }

    private static String sha256(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        java.io.FileInputStream in = new java.io.FileInputStream(path);
        try {
            byte[] buffer = new byte[32768];
            int count;
            while ((count = in.read(buffer)) >= 0) if (count != 0) digest.update(buffer, 0, count);
        } finally {
            in.close();
        }
        StringBuilder result = new StringBuilder();
        for (byte b : digest.digest()) result.append(String.format(Locale.ROOT, "%02x", b & 255));
        return result.toString();
    }

    private static void write(Writer out, Probe probe) throws Exception {
        long bits = probe.bits;
        StringBuilder categories = new StringBuilder();
        for (String category : probe.categories) {
            if (categories.length() != 0) categories.append(',');
            categories.append(category);
        }
        out.write(categories.toString());
        out.write('\t');
        out.write(hex(bits, 16));
        if (!supported(bits)) {
            out.write("\tREFUSE\t-\t-\n");
            return;
        }
        // Only supported generated inputs reach the JDK transcendental oracle.
        double x = Double.longBitsToDouble(bits);
        double y = Math.cos(x);
        float fy = (float) y;
        out.write("\tSUPPORTED\t");
        out.write(hex(Double.doubleToRawLongBits(y), 16));
        out.write('\t');
        out.write(hex(Float.floatToRawIntBits(fy) & 0xffffffffL, 8));
        out.write('\n');
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("usage: MathCosJava8Oracle OUTPUT.tsv");
        generate();
        Writer out = new BufferedWriter(new OutputStreamWriter(
                new FileOutputStream(args[0]), Charset.forName("US-ASCII")));
        try {
            out.write("categories\tinput_bits\tpolicy\tjava8_cos_bits\tjava8_float_bits\n");
            for (Probe probe : new ArrayList<Probe>(PROBES.values())) write(out, probe);
        } finally {
            out.close();
        }
        int supported = 0;
        for (Probe probe : PROBES.values()) if (supported(probe.bits)) supported++;
        System.out.println("unique_rows=" + PROBES.size());
        System.out.println("supported_rows=" + supported);
        System.out.println("refused_controls=" + (PROBES.size() - supported));
        System.out.println("grid_rows=" + GRID_SIZE);
        System.out.println("dyadic_positive_magnitudes=1608 (both signs)");
        System.out.println("random_magnitudes=" + RANDOM_COUNT + " (both signs, seed=0x434f535131323030)");
        System.out.println("formula=x=(double)i*6.283185307179586/65536");
        System.out.println("domain=finite raw |x|<=0x401921fb54442d18; refused rows have no oracle result");
        System.out.println("oracle_sha256=" + sha256(args[0]));
    }
}
