package bundle.m5cb.constants;

/** Exact CP4/CP6, fconst/dconst, subnormal, infinity and signed-zero fixtures. */
public strictfp class ConstantRoot {
    private static int fbits(float value) {
        return Float.floatToRawIntBits(value);
    }

    private static long dbits(double value) {
        return Double.doubleToRawLongBits(value);
    }

    public static int floatZero(int ignored) { return fbits(0.0f); }
    public static int floatOne(int ignored) { return fbits(1.0f); }
    public static int floatTwo(int ignored) { return fbits(2.0f); }
    public static int floatNegativeZero(int ignored) { return fbits(-0.0f); }
    public static int floatMinSubnormal(int ignored) { return fbits(0x0.000002p-126f); }
    public static int floatMinNormal(int ignored) { return fbits(0x1.0p-126f); }
    public static int floatMaxFinite(int ignored) { return fbits(0x1.fffffep127f); }
    public static int floatPositiveInfinity(int ignored) { return fbits(Float.intBitsToFloat(0x7f800000)); }

    public static int doubleZeroHigh(int ignored) { return (int) (dbits(0.0d) >>> 32); }
    public static int doubleOneHigh(int ignored) { return (int) (dbits(1.0d) >>> 32); }
    public static int doubleNegativeZeroHigh(int ignored) { return (int) (dbits(-0.0d) >>> 32); }
    public static int doubleMinSubnormalLow(int ignored) { return (int) dbits(0x0.0000000000001p-1022); }
    public static int doubleMinNormalHigh(int ignored) { return (int) (dbits(0x1.0p-1022) >>> 32); }
    public static int doubleMaxFiniteHigh(int ignored) { return (int) (dbits(0x1.fffffffffffffp1023) >>> 32); }
    public static int doublePositiveInfinityHigh(int ignored) {
        return (int) (dbits(Double.longBitsToDouble(0x7ff0000000000000L)) >>> 32);
    }
}
