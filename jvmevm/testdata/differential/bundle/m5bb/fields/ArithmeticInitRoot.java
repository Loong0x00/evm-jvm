package bundle.m5bb.fields;

public class ArithmeticInitRoot {
    static final long[] values = initialize();

    private static long[] initialize() {
        long[] target = null;
        int zero = 0;
        target[-1] = 0x123456789abcdef0L / (long) zero;
        return target;
    }

    public static int entry(int seed) {
        return (int) values[0] + seed;
    }
}
