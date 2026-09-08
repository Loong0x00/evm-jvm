package bundle.m5cd.basic;

/** Exact binary32/binary64 array cells and javac's category forms. */
public strictfp class BasicArrayRoot {
    private static long join(int high, int low) {
        return ((long) high << 32) | (low & 0xffffffffL);
    }

    private static float asFloat(int bits) {
        return Float.intBitsToFloat(bits);
    }

    private static double asDouble(int high, int low) {
        return Double.longBitsToDouble(join(high, low));
    }

    private static int rawFloat(float value) {
        return Float.floatToRawIntBits(value);
    }

    private static long rawDouble(double value) {
        return Double.doubleToRawLongBits(value);
    }

    private static int arithmeticFloat(float value) {
        return value != value ? 0x7fc00000 : rawFloat(value);
    }

    private static long arithmeticDouble(double value) {
        return value != value ? 0x7ff8000000000000L : rawDouble(value);
    }

    public static int floatDefault(int length) {
        float[] values = new float[length];
        return rawFloat(values[length - 1]);
    }

    public static int doubleDefaultHigh(int length) {
        double[] values = new double[length];
        return (int) (rawDouble(values[length - 1]) >>> 32);
    }

    public static int doubleDefaultLow(int length) {
        double[] values = new double[length];
        return (int) rawDouble(values[length - 1]);
    }

    public static int floatRoundTrip(int bits) {
        float[] values = new float[2];
        values[1] = asFloat(bits);
        return rawFloat(values[1]);
    }

    private static long doubleRoundTripBits(int high, int low) {
        double[] values = new double[2];
        values[1] = asDouble(high, low);
        return rawDouble(values[1]);
    }

    public static int doubleRoundTripHigh(int high, int low) {
        return (int) (doubleRoundTripBits(high, low) >>> 32);
    }

    public static int doubleRoundTripLow(int high, int low) {
        return (int) doubleRoundTripBits(high, low);
    }

    public static int floatCopy(int bits) {
        float[] source = new float[] { asFloat(bits) };
        float[] target = new float[1];
        target[0] = source[0];
        return rawFloat(target[0]);
    }

    private static long doubleCopyBits(int high, int low) {
        double[] source = new double[] { asDouble(high, low) };
        double[] target = new double[1];
        target[0] = source[0];
        return rawDouble(target[0]);
    }

    public static int doubleCopyHigh(int high, int low) {
        return (int) (doubleCopyBits(high, low) >>> 32);
    }

    public static int doubleCopyLow(int high, int low) {
        return (int) doubleCopyBits(high, low);
    }

    public static int floatAlias(int firstBits, int secondBits) {
        float[] values = new float[] { asFloat(firstBits), asFloat(secondBits) };
        float[] alias = values;
        alias[0] = alias[1];
        return rawFloat(values[0]);
    }

    private static long doubleAliasBits(int ah, int al, int bh, int bl) {
        double[] values = new double[] { asDouble(ah, al), asDouble(bh, bl) };
        double[] alias = values;
        alias[0] = alias[1];
        return rawDouble(values[0]);
    }

    public static int doubleAliasHigh(int ah, int al, int bh, int bl) {
        return (int) (doubleAliasBits(ah, al, bh, bl) >>> 32);
    }

    public static int doubleAliasLow(int ah, int al, int bh, int bl) {
        return (int) doubleAliasBits(ah, al, bh, bl);
    }

    public static int floatPostIncrement(int bits) {
        float[] values = new float[] { asFloat(bits) };
        values[0]++;
        return arithmeticFloat(values[0]);
    }

    public static int floatCompound(int leftBits, int rightBits) {
        float[] values = new float[] { asFloat(leftBits) };
        values[0] *= asFloat(rightBits);
        return arithmeticFloat(values[0]);
    }

    private static long doublePostIncrementBits(int high, int low) {
        double[] values = new double[] { asDouble(high, low) };
        values[0]++;
        return arithmeticDouble(values[0]);
    }

    public static int doublePostIncrementHigh(int high, int low) {
        return (int) (doublePostIncrementBits(high, low) >>> 32);
    }

    public static int doublePostIncrementLow(int high, int low) {
        return (int) doublePostIncrementBits(high, low);
    }

    private static long doubleCompoundBits(int ah, int al, int bh, int bl) {
        double[] values = new double[] { asDouble(ah, al) };
        values[0] /= asDouble(bh, bl);
        return arithmeticDouble(values[0]);
    }

    public static int doubleCompoundHigh(int ah, int al, int bh, int bl) {
        return (int) (doubleCompoundBits(ah, al, bh, bl) >>> 32);
    }

    public static int doubleCompoundLow(int ah, int al, int bh, int bl) {
        return (int) doubleCompoundBits(ah, al, bh, bl);
    }
}
