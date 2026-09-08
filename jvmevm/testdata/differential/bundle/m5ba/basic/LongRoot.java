package bundle.m5ba.basic;

/** Scalar long constants, arithmetic, conversions, shifts, locals, and javac category-2 stack forms. */
public class LongRoot {
    private static int fold(long value) {
        return (int) (value ^ (value >>> 32));
    }

    private static long join(int high, int low) {
        return ((long) high << 32) | ((long) low & 0xffffffffL);
    }

    private static long supplied(long value) { return value; }

    public static int constZero(int salt) { return fold(0L) + salt; }
    public static int constOne(int salt) { return fold(1L) + salt; }
    public static int constMinusOne(int salt) { return fold(-1L) + salt; }
    public static int constMax(int salt) { return fold(0x7fffffffffffffffL) + salt; }
    public static int constMin(int salt) { return fold(0x8000000000000000L) + salt; }
    public static int constBit32(int salt) { return fold(0x0000000100000000L) + salt; }
    public static int constPatterns(int salt) {
        return fold(0x0123456789abcdefL) ^ fold(0xfedcba9876543210L) ^ salt;
    }

    public static int addJoined(int ah, int al, int bh, int bl) {
        return fold(join(ah, al) + join(bh, bl));
    }
    public static int subtractJoined(int ah, int al, int bh, int bl) {
        return fold(join(ah, al) - join(bh, bl));
    }
    public static int multiply(int left, int right) { return fold((long) left * (long) right); }
    public static int multiplyWrap(int salt) {
        long factor = (long) (salt - salt) + 4L;
        return fold(0x4000000000000001L * factor) + salt;
    }
    public static int negateJoined(int high, int low) { return fold(-join(high, low)); }
    public static int negateMin(int salt) {
        long minimum = 0x8000000000000000L + (salt - salt);
        return fold(-minimum) + salt;
    }
    public static int andJoined(int ah, int al, int bh, int bl) { return fold(join(ah, al) & join(bh, bl)); }
    public static int orJoined(int ah, int al, int bh, int bl) { return fold(join(ah, al) | join(bh, bl)); }
    public static int xorJoined(int ah, int al, int bh, int bl) { return fold(join(ah, al) ^ join(bh, bl)); }

    public static int divide(int dividend, int divisor) { return fold((long) dividend / divisor); }
    public static int remainder(int dividend, int divisor) { return fold((long) dividend % divisor); }
    public static int divideWide(int divisor) { return fold(0x7123456789abcdefL / divisor); }
    public static int remainderWide(int divisor) { return fold(0x7123456789abcdefL % divisor); }
    public static int minDivideMinusOne(int salt) {
        long minimum = 0x8000000000000000L + (salt - salt);
        long minusOne = (long) (salt ^ salt) - 1L;
        return fold(minimum / minusOne) + salt;
    }
    public static int minRemainderMinusOne(int salt) {
        long minimum = 0x8000000000000000L + (salt - salt);
        long minusOne = (long) (salt ^ salt) - 1L;
        return fold(minimum % minusOne) + salt;
    }
    public static int divideZero(int value) { return fold((long) value / (value - value)); }
    public static int remainderZero(int value) { return fold((long) value % (value - value)); }

    public static int shiftLeft(int high, int low, int distance) { return fold(join(high, low) << distance); }
    public static int shiftRight(int high, int low, int distance) { return fold(join(high, low) >> distance); }
    public static int unsignedShiftRight(int high, int low, int distance) { return fold(join(high, low) >>> distance); }

    public static int compare(int ah, int al, int bh, int bl) {
        long a = join(ah, al);
        long b = join(bh, bl);
        return a < b ? -1 : (a == b ? 0 : 1);
    }
    public static int compareExtremes(int choose) {
        long a = choose == 0 ? 0x8000000000000000L : 0x7fffffffffffffffL;
        long b = choose == 0 ? 0x7fffffffffffffffL : 0x8000000000000000L;
        return a < b ? -1 : (a == b ? 0 : 1);
    }
    public static int intToLong(int value) { return fold((long) value); }
    public static int longToInt(int high, int low) { return (int) join(high, low); }

    public static int oddLocal(int value) {
        long atOddSlot = (long) value * 0x100000001L;
        atOddSlot ^= 0x55aa55aa55aa55aaL;
        return fold(atOddSlot);
    }
    public static int localPostIncrement(int value) {
        long current = join(value, value ^ 0x55aa55aa);
        long old = current++;
        return fold(old) ^ fold(current);
    }
    public static int localPreIncrement(int value) {
        long current = join(value, ~value);
        long now = ++current;
        return fold(now) ^ fold(current);
    }
    public static int localAssignmentExpression(int value) {
        long first;
        long second = (first = join(value, value + 1));
        return fold(first) + fold(second);
    }
    public static int discardLongResult(int value) {
        supplied(join(value, ~value));
        return value ^ 0x13579bdf;
    }
    public static int modestLoop(int count) {
        long total = 0L;
        for (int i = 0; i < count; i++) total += (long) i * 0x100000001L;
        return fold(total);
    }
}
