package bundle.m5cc.scalar;

/** Bit-exact binary64 arithmetic roots in an ordinary (non-strictfp) class. */
public class DoubleArithmeticRoot {
    private static long join(int high, int low) {
        return ((long) high << 32) | (low & 0xffffffffL);
    }

    private static double value(int high, int low) {
        return Double.longBitsToDouble(join(high, low));
    }

    private static long result(double value) {
        // Normalize only generated arithmetic NaNs. All other bits are raw.
        return value != value ? 0x7ff8000000000000L : Double.doubleToRawLongBits(value);
    }

    private static double addValue(int ah, int al, int bh, int bl) {
        return value(ah, al) + value(bh, bl);
    }
    private static double subtractValue(int ah, int al, int bh, int bl) {
        return value(ah, al) - value(bh, bl);
    }
    private static double multiplyValue(int ah, int al, int bh, int bl) {
        return value(ah, al) * value(bh, bl);
    }
    private static double divideValue(int ah, int al, int bh, int bl) {
        return value(ah, al) / value(bh, bl);
    }
    private static double remainderValue(int ah, int al, int bh, int bl) {
        return value(ah, al) % value(bh, bl);
    }
    private static double remainder16Value(int ah, int al, int bh, int bl) {
        double left = value(ah, al);
        double right = value(bh, bl);
        double remainder = 0.0d;
        for (int i = 0; i < 16; i++) remainder = left % right;
        return remainder;
    }

    public static int addHigh(int ah, int al, int bh, int bl) {
        return (int) (result(addValue(ah, al, bh, bl)) >>> 32);
    }
    public static int addLow(int ah, int al, int bh, int bl) {
        return (int) result(addValue(ah, al, bh, bl));
    }
    public static int subtractHigh(int ah, int al, int bh, int bl) {
        return (int) (result(subtractValue(ah, al, bh, bl)) >>> 32);
    }
    public static int subtractLow(int ah, int al, int bh, int bl) {
        return (int) result(subtractValue(ah, al, bh, bl));
    }
    public static int multiplyHigh(int ah, int al, int bh, int bl) {
        return (int) (result(multiplyValue(ah, al, bh, bl)) >>> 32);
    }
    public static int multiplyLow(int ah, int al, int bh, int bl) {
        return (int) result(multiplyValue(ah, al, bh, bl));
    }
    public static int divideHigh(int ah, int al, int bh, int bl) {
        return (int) (result(divideValue(ah, al, bh, bl)) >>> 32);
    }
    public static int divideLow(int ah, int al, int bh, int bl) {
        return (int) result(divideValue(ah, al, bh, bl));
    }
    public static int remainderHigh(int ah, int al, int bh, int bl) {
        return (int) (result(remainderValue(ah, al, bh, bl)) >>> 32);
    }
    public static int remainderLow(int ah, int al, int bh, int bl) {
        return (int) result(remainderValue(ah, al, bh, bl));
    }
    public static int remainder16High(int ah, int al, int bh, int bl) {
        return (int) (result(remainder16Value(ah, al, bh, bl)) >>> 32);
    }
    public static int remainder16Low(int ah, int al, int bh, int bl) {
        return (int) result(remainder16Value(ah, al, bh, bl));
    }
}
