import java.io.BufferedWriter;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.Charset;
import java.security.MessageDigest;

/**
 * Standalone generated-input host oracle. This is test/evidence code only.
 * It has no project/runtime dependencies and loads no Minecraft artifacts.
 */
public strictfp final class MathSinOracle {
    private static final int GRID_SIZE = 65536;
    private static final long[][] SPECIALS = new long[][] {
        {0x0000000000000000L, 0}, // +0
        {0x8000000000000000L, 1}, // -0
        {0x0000000000000001L, 2}, // +min subnormal
        {0x8000000000000001L, 3}, // -min subnormal
        {0x0010000000000000L, 4}, // +min normal
        {0x8010000000000000L, 5}, // -min normal
        {0x7fefffffffffffffL, 6}, // +max finite
        {0xffefffffffffffffL, 7}, // -max finite
        {0x3ff921fb54442d17L, 8}, // below nearest binary64 pi/2
        {0x3ff921fb54442d18L, 9}, // nearest binary64 pi/2
        {0x3ff921fb54442d19L, 10}, // above nearest binary64 pi/2
        {0x400921fb54442d17L, 11}, // below nearest binary64 pi
        {0x400921fb54442d18L, 12}, // nearest binary64 pi
        {0x400921fb54442d19L, 13}, // above nearest binary64 pi
        {0x401921fb54442d17L, 14}, // below nearest binary64 2*pi
        {0x401921fb54442d18L, 15}, // nearest binary64 2*pi
        {0x401921fb54442d19L, 16}, // above nearest binary64 2*pi
        {0x7ff0000000000000L, 17}, // +infinity
        {0xfff0000000000000L, 18}, // -infinity
        {0x7ff8000000000001L, 19}, // positive quiet NaN, payload 1
        {0xfff8000000000001L, 20}, // negative quiet NaN, payload 1
        {0x7ff0000000000001L, 21}, // positive signaling NaN, payload 1
        {0xfff0000000000001L, 22}  // negative signaling NaN, payload 1
    };

    private MathSinOracle() { }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            throw new IllegalArgumentException("usage: MathSinOracle OUTPUT.tsv");
        }
        String path = args[0];
        Writer writer = new BufferedWriter(new OutputStreamWriter(
                new FileOutputStream(path), Charset.forName("US-ASCII")));
        try {
            writer.write("kind\tkey\tx_raw_bits\tmath_sin_raw_bits\tfloat_cast_raw_bits\n");
            for (int i = 0; i < GRID_SIZE; i++) {
                double x = (double) i * 6.283185307179586 / 65536;
                writeRow(writer, "GRID", Integer.toString(i), x);
            }
            for (int i = 0; i < SPECIALS.length; i++) {
                writeRow(writer, "EDGE", edgeName((int) SPECIALS[i][1]),
                        Double.longBitsToDouble(SPECIALS[i][0]));
            }
        } finally {
            writer.close();
        }
        System.out.println("grid_rows=" + GRID_SIZE);
        System.out.println("edge_rows=" + SPECIALS.length);
        System.out.println("total_rows=" + (GRID_SIZE + SPECIALS.length));
        System.out.println("fixture_sha256=" + sha256(path));
        System.out.println("formula=x=(double)i*6.283185307179586/65536");
        System.out.println("outputs=raw bits of Math.sin(x), then raw bits of (float)Math.sin(x)");
    }

    private static void writeRow(Writer writer, String kind, String key, double x)
            throws Exception {
        double y = Math.sin(x);
        float fy = (float) y;
        writer.write(kind);
        writer.write('\t');
        writer.write(key);
        writer.write('\t');
        writer.write(hex(Double.doubleToRawLongBits(x), 16));
        writer.write('\t');
        writer.write(hex(Double.doubleToRawLongBits(y), 16));
        writer.write('\t');
        writer.write(hex(Float.floatToRawIntBits(fy) & 0xffffffffL, 8));
        writer.write('\n');
    }

    private static String edgeName(int id) {
        switch (id) {
            case 0: return "positive-zero";
            case 1: return "negative-zero";
            case 2: return "positive-min-subnormal";
            case 3: return "negative-min-subnormal";
            case 4: return "positive-min-normal";
            case 5: return "negative-min-normal";
            case 6: return "positive-max-finite";
            case 7: return "negative-max-finite";
            case 8: return "pi-over-2-below";
            case 9: return "pi-over-2-nearest";
            case 10: return "pi-over-2-above";
            case 11: return "pi-below";
            case 12: return "pi-nearest";
            case 13: return "pi-above";
            case 14: return "two-pi-below";
            case 15: return "two-pi-nearest";
            case 16: return "two-pi-above";
            case 17: return "positive-infinity";
            case 18: return "negative-infinity";
            case 19: return "positive-qnan-payload-1";
            case 20: return "negative-qnan-payload-1";
            case 21: return "positive-snan-payload-1";
            case 22: return "negative-snan-payload-1";
            default: throw new IllegalArgumentException("unknown edge id " + id);
        }
    }

    private static String hex(long value, int width) {
        String digits = Long.toHexString(value);
        StringBuilder result = new StringBuilder(width);
        for (int i = digits.length(); i < width; i++) {
            result.append('0');
        }
        result.append(digits);
        return result.toString();
    }

    private static String sha256(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        FileInputStream input = new FileInputStream(path);
        try {
            byte[] buffer = new byte[8192];
            int count;
            while ((count = input.read(buffer)) != -1) {
                digest.update(buffer, 0, count);
            }
        } finally {
            input.close();
        }
        byte[] hash = digest.digest();
        StringBuilder result = new StringBuilder(64);
        for (int i = 0; i < hash.length; i++) {
            int value = hash[i] & 0xff;
            if (value < 16) result.append('0');
            result.append(Integer.toHexString(value));
        }
        return result.toString();
    }

}
