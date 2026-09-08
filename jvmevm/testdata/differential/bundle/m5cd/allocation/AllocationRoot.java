package bundle.m5cd.allocation;

/** Backing-table/handle order and all primitive leaf kinds in one stage. */
public class AllocationRoot {
    private static long join(int high, int low) {
        return ((long) high << 32) | (low & 0xffffffffL);
    }

    private static float f(int bits) { return Float.intBitsToFloat(bits); }
    private static double d(int high, int low) { return Double.longBitsToDouble(join(high, low)); }
    private static int fr(float value) { return Float.floatToRawIntBits(value); }
    private static long dr(double value) { return Double.doubleToRawLongBits(value); }
    private static int fold(long value) { return (int) (value ^ (value >>> 32)); }

    public static int floatFirst(int bits) {
        float[] floats = new float[] { f(bits) };
        double[] doubles = new double[1];
        long[] longs = new long[] { bits };
        Object[] refs = new Object[] { floats, doubles, longs };
        AllocationCell cell = new AllocationCell(bits);
        return fr(((float[]) refs[0])[0]) ^ fold(((long[]) refs[2])[0]) ^ cell.value;
    }

    public static int doubleFirst(int high, int low) {
        double[] doubles = new double[] { d(high, low) };
        float[] floats = new float[1];
        int[] ints = new int[] { low };
        AllocationCell cell = new AllocationCell(high);
        Object[] refs = new Object[] { doubles, floats, ints, cell };
        return fold(dr(((double[]) refs[0])[0])) ^ ((int[]) refs[2])[0] ^ ((AllocationCell) refs[3]).value;
    }

    public static int longFirst(int seed) {
        long[] longs = new long[] { 0x123456789abcdef0L };
        float[] floats = new float[] { f(0x80000000) };
        double[] doubles = new double[] { d(0x7ff81234, 0x56789abc) };
        Object[] refs = new Object[] { longs, floats, doubles };
        return fold(((long[]) refs[0])[0]) ^ fr(((float[]) refs[1])[0]) ^ fold(dr(((double[]) refs[2])[0])) ^ seed;
    }

    public static int referenceFirst(int seed) {
        Object[] refs = new Object[3];
        float[] floats = new float[] { seed };
        double[] doubles = new double[] { -0.0d };
        refs[0] = floats;
        refs[1] = doubles;
        refs[2] = refs;
        return fr(((float[]) refs[0])[0]) ^ fold(dr(((double[]) refs[1])[0])) ^ (refs[2] == refs ? 17 : 29);
    }

    public static int objectFirst(int seed) {
        AllocationCell cell = new AllocationCell(seed);
        double[] doubles = new double[] { seed };
        float[] floats = new float[] { -0.0f };
        Object[] refs = new Object[] { cell, doubles, floats };
        return ((AllocationCell) refs[0]).value ^ fold(dr(((double[]) refs[1])[0])) ^ fr(((float[]) refs[2])[0]);
    }

    public static int allPrimitiveDefaults(int seed) {
        boolean[] z = new boolean[1];
        byte[] b = new byte[1];
        char[] c = new char[1];
        short[] s = new short[1];
        int[] i = new int[1];
        long[] j = new long[1];
        float[] f = new float[1];
        double[] d = new double[1];
        int result = !z[0] ? 1 : 0;
        result = result * 2 + (b[0] == 0 ? 1 : 0);
        result = result * 2 + (c[0] == 0 ? 1 : 0);
        result = result * 2 + (s[0] == 0 ? 1 : 0);
        result = result * 2 + (i[0] == 0 ? 1 : 0);
        result = result * 2 + (j[0] == 0L ? 1 : 0);
        result = result * 2 + (fr(f[0]) == 0 ? 1 : 0);
        result = result * 2 + (dr(d[0]) == 0L ? 1 : 0);
        return result * 31 + seed;
    }

    public static int allPrimitiveWrites(int seed) {
        boolean[] z = new boolean[] { seed != 0 };
        byte[] b = new byte[] { (byte) seed };
        char[] c = new char[] { (char) seed };
        short[] s = new short[] { (short) seed };
        int[] i = new int[] { seed };
        long[] j = new long[] { ((long) seed << 32) | (seed & 0xffffffffL) };
        float[] fv = new float[] { f(seed) };
        double[] dv = new double[] { d(seed, ~seed) };
        return (z[0] ? 1 : 0) + b[0] + c[0] + s[0] + i[0] + fold(j[0]) + fr(fv[0]) + fold(dr(dv[0]));
    }

    public static int mixedAliases(int seed) {
        float[] floats = new float[] { f(0x7fc12345) };
        double[] doubles = new double[] { d(0xfff81234, 0x56789abc) };
        Object[] refs = new Object[] { floats, doubles, floats, doubles };
        int identity = refs[0] == refs[2] && refs[1] == refs[3] && refs[0] != refs[1] ? 701 : 907;
        return fr(((float[]) refs[2])[0]) ^ fold(dr(((double[]) refs[3])[0])) ^ identity ^ seed;
    }
}

class AllocationCell {
    int value;

    AllocationCell(int value) {
        this.value = value;
    }
}
