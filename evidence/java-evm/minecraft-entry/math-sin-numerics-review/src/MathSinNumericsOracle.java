import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.Charset;

/** Standalone JDK 8 raw-bit Math.sin oracle for generated test inputs only. */
public strictfp final class MathSinNumericsOracle {
    private static final long MAX_X_BITS = 0x401921fb54442d18L;

    private MathSinNumericsOracle() { }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            throw new IllegalArgumentException("usage: MathSinNumericsOracle INPUT.tsv OUTPUT.tsv");
        }
        BufferedReader input = new BufferedReader(new InputStreamReader(
                new FileInputStream(args[0]), Charset.forName("US-ASCII")));
        Writer output = new BufferedWriter(new OutputStreamWriter(
                new FileOutputStream(args[1]), Charset.forName("US-ASCII")));
        int count = 0;
        try {
            String header = input.readLine();
            if (!"kind\tkey\tx_raw_bits".equals(header)) {
                throw new IllegalArgumentException("unexpected input header: " + header);
            }
            output.write("kind\tkey\tx_raw_bits\tjdk_sin_raw_bits\tjdk_float_raw_bits\n");
            String line;
            while ((line = input.readLine()) != null) {
                String[] fields = line.split("\\t", -1);
                if (fields.length != 3) {
                    throw new IllegalArgumentException("malformed input row " + (count + 2));
                }
                long raw = Long.parseUnsignedLong(fields[2], 16);
                long magnitude = raw & 0x7fffffffffffffffL;
                if (magnitude > MAX_X_BITS) {
                    throw new IllegalArgumentException("input outside finite supported range: " + fields[2]);
                }
                double x = Double.longBitsToDouble(raw);
                double y = Math.sin(x);
                float fy = (float) y;
                output.write(fields[0]);
                output.write('\t');
                output.write(fields[1]);
                output.write('\t');
                output.write(hex(raw, 16));
                output.write('\t');
                output.write(hex(Double.doubleToRawLongBits(y), 16));
                output.write('\t');
                output.write(hex(Float.floatToRawIntBits(fy) & 0xffffffffL, 8));
                output.write('\n');
                count++;
            }
        } finally {
            input.close();
            output.close();
        }
        System.out.println("oracle_rows=" + count);
        System.out.println("input_domain=finite raw magnitude <= 0x" + hex(MAX_X_BITS, 16));
        System.out.println("oracle=Math.sin(double), followed by Java double-to-float cast");
    }

    private static String hex(long value, int width) {
        String digits = Long.toHexString(value);
        StringBuilder result = new StringBuilder(width);
        for (int i = digits.length(); i < width; i++) result.append('0');
        return result.append(digits).toString();
    }
}
