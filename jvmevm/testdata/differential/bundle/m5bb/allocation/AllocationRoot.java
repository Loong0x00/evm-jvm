package bundle.m5bb.allocation;

public class AllocationRoot {
    private static int fold(long value) {
        return (int) (value ^ (value >>> 32));
    }

    public static int objectIntRefLong(int seed) {
        AllocationCell cell = new AllocationCell(seed);
        int[] ints = new int[] { seed + 1 };
        Object[] refs = new Object[] { cell, ints };
        long[] longs = new long[] { 0x123456789abcdef0L, seed };
        return fold(longs[0] + longs[1]) + ints[0] +
            (refs[0] == cell ? 10 : 20) + (refs[1] == ints ? 30 : 40);
    }

    public static int longObjectRef(int seed) {
        long[] longs = new long[] { Long.MIN_VALUE, seed };
        AllocationCell cell = new AllocationCell(seed + 1);
        Object[] refs = new Object[] { longs, cell };
        return fold(((long[]) refs[0])[0] + longs[1]) +
            (((AllocationCell) refs[1]).value == seed + 1 ? 50 : 60);
    }

    public static int narrowThenLong(int seed) {
        byte[] bytes = new byte[] { (byte) seed };
        short[] shorts = new short[] { (short) (seed * 3) };
        char[] chars = new char[] { (char) seed };
        boolean[] flags = new boolean[] { seed != 0 };
        long[] longs = new long[] { ((long) seed << 48) ^ 0x0000abcdef012345L };
        return fold(longs[0]) + bytes[0] + shorts[0] + chars[0] + (flags[0] ? 1 : 0);
    }

    public static int longThenNarrow(int seed) {
        long[] longs = new long[] { 0xfedcba9876543210L + seed };
        boolean[] flags = new boolean[1];
        char[] chars = new char[1];
        short[] shorts = new short[1];
        byte[] bytes = new byte[1];
        return fold(longs[0]) + (flags[0] ? 100 : 0) + chars[0] + shorts[0] + bytes[0];
    }

    public static int refMatrixLongObject(int seed) {
        Object[][] refs = new Object[1][1];
        long[][] longs = new long[1][1];
        AllocationCell cell = new AllocationCell(seed);
        refs[0][0] = longs;
        longs[0][0] = 0x700000008L + cell.value;
        return fold(((long[][]) refs[0][0])[0][0]);
    }

    public static int mixedIdentity(int seed) {
        long[] first = new long[0];
        AllocationCell cell = new AllocationCell(seed);
        int[] middle = new int[0];
        long[] second = new long[0];
        Object[] refs = new Object[] { first, cell, middle, second };
        int bits = refs[0] == first ? 1 : 0;
        bits = bits * 2 + (refs[1] == cell ? 1 : 0);
        bits = bits * 2 + (refs[2] == middle ? 1 : 0);
        bits = bits * 2 + (refs[3] == second ? 1 : 0);
        bits = bits * 2 + (first == second ? 1 : 0);
        return bits * 31 + seed;
    }

    public static int defaultsStayDistinct(int seed) {
        AllocationCell cell = new AllocationCell(0);
        long[] longs = new long[1];
        Object[] refs = new Object[1];
        int[] ints = new int[1];
        int result = longs[0] == 0L ? 1 : 0;
        result = result * 2 + (refs[0] == null ? 1 : 0);
        result = result * 2 + (ints[0] == 0 ? 1 : 0);
        result = result * 2 + (cell.value == 0 ? 1 : 0);
        return result * 31 + seed;
    }

    public static int aliasesAcrossObjectArray(int seed) {
        long[] values = new long[] { seed };
        Object[] refs = new Object[] { values };
        long[] alias = (long[]) refs[0];
        alias[0] += 0x100000001L;
        return fold(values[0]) + (alias == values ? 701 : 907);
    }
}

class AllocationCell {
    int value;

    AllocationCell(int value) {
        this.value = value;
    }
}
