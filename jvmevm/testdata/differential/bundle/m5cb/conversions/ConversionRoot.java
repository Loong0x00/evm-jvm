package bundle.m5cb.conversions;

/** Trusted scalar IEEE conversion fixtures. No floating-point arithmetic is used. */
public strictfp class ConversionRoot {
    private static long join(int high, int low) {
        return ((long) high << 32) | (low & 0xffffffffL);
    }

    private static double doubleFromWords(int high, int low) {
        return Double.longBitsToDouble(join(high, low));
    }

    private static long normalizedDoubleBits(double value) {
        if (value != value) {
            return 0x7ff8000000000000L;
        }
        return Double.doubleToRawLongBits(value);
    }

    private static int normalizedFloatBits(float value) {
        if (value != value) {
            return 0x7fc00000;
        }
        return Float.floatToRawIntBits(value);
    }

    public static int i2fBits(int value) {
        return Float.floatToRawIntBits((float) value);
    }

    public static int i2dHigh(int value) {
        return (int) (Double.doubleToRawLongBits((double) value) >>> 32);
    }

    public static int i2dLow(int value) {
        return (int) Double.doubleToRawLongBits((double) value);
    }

    public static int l2fBits(int high, int low) {
        return Float.floatToRawIntBits((float) join(high, low));
    }

    public static int l2dHigh(int high, int low) {
        return (int) (Double.doubleToRawLongBits((double) join(high, low)) >>> 32);
    }

    public static int l2dLow(int high, int low) {
        return (int) Double.doubleToRawLongBits((double) join(high, low));
    }

    public static int f2i(int bits) {
        return (int) Float.intBitsToFloat(bits);
    }

    public static int f2lHigh(int bits) {
        return (int) (((long) Float.intBitsToFloat(bits)) >>> 32);
    }

    public static int f2lLow(int bits) {
        return (int) ((long) Float.intBitsToFloat(bits));
    }

    // The Java specification does not promise a NaN payload for widening.
    // Normalize only NaN; every finite value and signed zero stays raw-bit exact.
    public static int f2dHigh(int bits) {
        long raw = normalizedDoubleBits((double) Float.intBitsToFloat(bits));
        return (int) (raw >>> 32);
    }

    public static int f2dLow(int bits) {
        return (int) normalizedDoubleBits((double) Float.intBitsToFloat(bits));
    }

    public static int d2i(int high, int low) {
        return (int) doubleFromWords(high, low);
    }

    public static int d2lHigh(int high, int low) {
        return (int) (((long) doubleFromWords(high, low)) >>> 32);
    }

    public static int d2lLow(int high, int low) {
        return (int) ((long) doubleFromWords(high, low));
    }

    // Narrowing NaN payloads are likewise unspecified, so only NaN is canonicalized.
    public static int d2fBits(int high, int low) {
        return normalizedFloatBits((float) doubleFromWords(high, low));
    }
}
