package bundle.m5a.arrays;

/** newarray/baload/caload/saload stores plus narrow-array transport and multidimensional allocation. */
public class ArrayRoot {
    public static int byteDefaults(int value) {
        byte[] values = new byte[3];
        return values.length == 3 && values[0] == 0 && values[2] == 0 ? value : -1;
    }
    public static int byteStoreLoad(int value) { byte[] values = new byte[2]; values[1] = (byte) value; return values[1]; }
    public static int byteLoop(int value) {
        byte[] values = new byte[4];
        int sum = 0;
        for (int i = 0; i < values.length; i++) { values[i] = (byte) (value + i * 127); sum += values[i]; }
        return sum;
    }
    public static int byteCompound(int value) {
        byte[] values = new byte[1]; values[0] = (byte) value; values[0] += 129; return values[0];
    }

    public static int booleanDefaults(int value) {
        boolean[] values = new boolean[3];
        return !values[0] && !values[2] ? value : -1;
    }
    public static int booleanStoreLoad(int value) {
        boolean[] values = new boolean[2]; values[1] = (value & 1) != 0; return values[1] ? 1 : 0;
    }
    public static int booleanToggleLoop(int value) {
        boolean[] values = new boolean[4];
        boolean current = (value & 1) != 0;
        int trace = 0;
        for (int i = 0; i < values.length; i++) { values[i] = current; trace = trace * 10 + (values[i] ? 1 : 0); current = !current; }
        return trace;
    }

    public static int charDefaults(int value) {
        char[] values = new char[2]; return values[0] == 0 && values[1] == 0 ? value : -1;
    }
    public static int charStoreLoad(int value) { char[] values = new char[1]; values[0] = (char) value; return values[0]; }
    public static int charLoop(int value) {
        char[] values = new char[3]; int sum = 0;
        for (int i = 0; i < values.length; i++) { values[i] = (char) (value + i * 40000); sum += values[i]; }
        return sum;
    }

    public static int shortDefaults(int value) {
        short[] values = new short[2]; return values[0] == 0 && values[1] == 0 ? value : -1;
    }
    public static int shortStoreLoad(int value) { short[] values = new short[1]; values[0] = (short) value; return values[0]; }
    public static int shortLoop(int value) {
        short[] values = new short[3]; int sum = 0;
        for (int i = 0; i < values.length; i++) { values[i] = (short) (value + i * 30000); sum += values[i]; }
        return sum;
    }

    public static int staticByteField(int value) {
        ArrayFields.STATIC_BYTES = new byte[2]; ArrayFields.STATIC_BYTES[1] = (byte) value; return ArrayFields.STATIC_BYTES[1];
    }
    public static int instanceBooleanField(int value) {
        ArrayFields fields = new ArrayFields(); fields.booleans = new boolean[1]; fields.booleans[0] = (value & 1) != 0; return fields.booleans[0] ? 1 : 0;
    }
    public static int finalCharField(int value) {
        ArrayFields fields = new ArrayFields(2); fields.chars[1] = (char) value; return fields.chars[1];
    }

    private static byte[] byteFactory(int value) { byte[] result = new byte[1]; result[0] = (byte) value; return result; }
    private static int byteConsumer(byte[] values) { return values[0]; }
    public static int staticByteRoundTrip(int value) { return byteConsumer(byteFactory(value)); }

    private short[] privateShort(short value) { short[] result = new short[1]; result[0] = value; return result; }
    public static int privateShortRoundTrip(int value) { return new ArrayRoot().privateShort((short) value)[0]; }

    public static int virtualBooleanRoundTrip(int value) {
        boolean[] values = new boolean[1]; return new ArrayVirtualChild().flip(values, (value & 1) != 0) ? 1 : 0;
    }
    public static int defaultCharRoundTrip(int value) {
        char[] values = new char[1]; return new ArrayDefaultImpl().place(values, (char) value);
    }

    public static int byteMatrix(int value) {
        byte[][] values = new byte[2][3]; values[1][2] = (byte) value;
        return values[0] != values[1] && values[0][0] == 0 ? values[1][2] : -999;
    }
    public static int booleanPartialMatrix(int value) {
        boolean[][] values = new boolean[2][]; values[1] = new boolean[1]; values[1][0] = (value & 1) != 0;
        return values[0] == null && values[1][0] ? 1 : 0;
    }
    public static int charCube(int value) {
        char[][][] values = new char[1][2][1]; values[0][1][0] = (char) value; return values[0][1][0];
    }
    public static int shortMatrix(int value) {
        short[][] values = new short[2][1]; values[0][0] = (short) value; values[1][0] = (short) (value + 1);
        return values[0][0] + values[1][0];
    }
}

class ArrayFields {
    static byte[] STATIC_BYTES;
    boolean[] booleans;
    final char[] chars;
    ArrayFields() { chars = new char[0]; }
    ArrayFields(int length) { chars = new char[length]; }
}
class ArrayVirtual { boolean flip(boolean[] values, boolean value) { values[0] = value; return values[0]; } }
class ArrayVirtualChild extends ArrayVirtual { boolean flip(boolean[] values, boolean value) { values[0] = !value; return values[0]; } }
interface ArrayDefault { default char place(char[] values, char value) { values[0] = value; return values[0]; } }
class ArrayDefaultImpl implements ArrayDefault {}
