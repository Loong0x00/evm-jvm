package bundle.m5a.init;

/** Narrow fields/arrays initialized in the VM, including wrapped initializer failures. */
public class InitRoot {
    public static int initializedValues(int value) {
        return Initialized.B * 1000000 + Initialized.S * 10 + Initialized.C + (Initialized.Z ? 1 : 0)
            + Initialized.BYTES[0] + Initialized.CHARS[0] + value;
    }
    public static int initializedOnce(int value) {
        return Once.B + Once.B + Once.trace * 100 + value;
    }
    public static int byteNegativeWrapped(int value) { return ByteNegative.VALUE + value; }
    public static int arrayStoreWrapped(int value) { return StoreFailure.VALUE + value; }
    public static int castWrapped(int value) { return CastFailure.VALUE + value; }
    public static int arithmeticWrapped(int value) { return ArithmeticFailure.B + value; }
}

class Initialized {
    static byte B = (byte) 255;
    static short S = (short) 65535;
    static char C = (char) -1;
    static boolean Z = true;
    static byte[] BYTES = new byte[1];
    static char[] CHARS = new char[1];
    static { BYTES[0] = (byte) 130; CHARS[0] = (char) -2; }
}
class Once {
    static int trace;
    static byte B = mark();
    static byte mark() { trace++; return (byte) 255; }
}
class ByteNegative { static int VALUE = new byte[-1].length; }
class StoreFailure {
    static int VALUE = fail();
    static int fail() { byte[][] actual = new byte[1][]; Object[] widened = actual; widened[0] = new boolean[1]; return 1; }
}
class CastFailure {
    static int VALUE = fail();
    static int fail() { Object object = new short[1]; return ((char[]) object)[0]; }
}
class ArithmeticFailure {
    static byte B = (byte) divide();
    static int divide() { return 1 / 0; }
}
