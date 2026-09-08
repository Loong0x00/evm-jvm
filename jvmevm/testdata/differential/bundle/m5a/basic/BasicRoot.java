package bundle.m5a.basic;

/** Source-valid wrappers around Java's four narrow int-like primitive types. */
public class BasicRoot {
    private static byte byteReturn(int value) { return (byte) value; }
    private static short shortReturn(int value) { return (short) value; }
    private static char charReturn(int value) { return (char) value; }
    private static boolean booleanReturn(int value) { return (value & 1) != 0; }

    private static int byteArgument(byte value) { return value; }
    private static int shortArgument(short value) { return value; }
    private static int charArgument(char value) { return value; }
    private static int booleanArgument(boolean value) { return value ? 1 : 0; }

    public static int byteBoundary(int value) { return byteReturn(value); }
    public static int shortBoundary(int value) { return shortReturn(value); }
    public static int charBoundary(int value) { return charReturn(value); }
    public static int booleanBoundary(int value) { return booleanReturn(value) ? 1 : 0; }
    public static int byteParameter(int value) { return byteArgument((byte) value); }
    public static int shortParameter(int value) { return shortArgument((short) value); }
    public static int charParameter(int value) { return charArgument((char) value); }
    public static int booleanParameter(int value) { return booleanArgument((value & 1) != 0); }

    public static int byteIncrementOverflow(int value) {
        byte current = (byte) value;
        current++;
        return current;
    }

    public static int shortCompoundOverflow(int value) {
        short current = (short) value;
        current += 32769;
        return current;
    }

    public static int charDecrementWrap(int value) {
        char current = (char) value;
        current--;
        return current;
    }

    public static int byteLoop(int value) {
        byte current = (byte) value;
        int sum = 0;
        for (int i = 0; i < 5; i++) {
            sum += current;
            current += 63;
        }
        return sum * 1000 + current;
    }

    public static int shortLoop(int value) {
        short current = (short) value;
        int sum = 0;
        for (int i = 0; i < 4; i++) {
            current = (short) (current * 3 + 10001);
            sum += current;
        }
        return sum;
    }

    public static int charUnsignedCompare(int value) {
        char current = (char) value;
        return current > 32767 ? current : -current;
    }

    public static int charLoopWrap(int value) {
        char current = (char) value;
        for (int i = 0; i < 4; i++) current += 20000;
        return current;
    }

    public static int booleanToggleLoop(int value) {
        boolean bit = (value & 1) != 0;
        int trace = 0;
        for (int i = 0; i < 5; i++) {
            trace = trace * 10 + (bit ? 1 : 0);
            bit = !bit;
        }
        return trace;
    }

    public static int mixedConversions(int value) {
        byte b = (byte) value;
        short s = (short) (b * 257);
        char c = (char) (s - 1);
        return b + s + c;
    }

    public static int intOverflowThenNarrow(int value) {
        int overflow = value * 65537 + 2147483647;
        return byteReturn(overflow) * 100000 + shortReturn(overflow) + charReturn(overflow);
    }
}
