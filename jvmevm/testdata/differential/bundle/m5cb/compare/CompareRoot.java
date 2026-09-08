package bundle.m5cb.compare;

/** Comparison, signed-zero, quiet-NaN, and exact sign-negation fixtures. */
public strictfp class CompareRoot {
    private static long join(int high, int low) {
        return ((long) high << 32) | (low & 0xffffffffL);
    }

    private static float asFloat(int bits) {
        return Float.intBitsToFloat(bits);
    }

    private static double asDouble(int high, int low) {
        return Double.longBitsToDouble(join(high, low));
    }

    // javac emits fcmpl for the greater-than branch; NaN therefore maps to -1.
    public static int floatCmpl(int leftBits, int rightBits) {
        float left = asFloat(leftBits);
        float right = asFloat(rightBits);
        if (left > right) return 1;
        if (left == right) return 0;
        return -1;
    }

    // javac emits fcmpg for the less-than branch; NaN therefore maps to +1.
    public static int floatCmpg(int leftBits, int rightBits) {
        float left = asFloat(leftBits);
        float right = asFloat(rightBits);
        if (left < right) return -1;
        if (left == right) return 0;
        return 1;
    }

    public static int doubleCmpl(int leftHigh, int leftLow, int rightHigh, int rightLow) {
        double left = asDouble(leftHigh, leftLow);
        double right = asDouble(rightHigh, rightLow);
        if (left > right) return 1;
        if (left == right) return 0;
        return -1;
    }

    public static int doubleCmpg(int leftHigh, int leftLow, int rightHigh, int rightLow) {
        double left = asDouble(leftHigh, leftLow);
        double right = asDouble(rightHigh, rightLow);
        if (left < right) return -1;
        if (left == right) return 0;
        return 1;
    }

    public static int floatNegBits(int bits) {
        float value = asFloat(bits);
        return Float.floatToRawIntBits(-value);
    }

    public static int doubleNegHigh(int high, int low) {
        long bits = Double.doubleToRawLongBits(-asDouble(high, low));
        return (int) (bits >>> 32);
    }

    public static int doubleNegLow(int high, int low) {
        return (int) Double.doubleToRawLongBits(-asDouble(high, low));
    }
}
