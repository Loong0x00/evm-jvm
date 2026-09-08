package bundle.m5cd.nested;

public class NestedRoot {
    private static long join(int high, int low) {
        return ((long) high << 32) | (low & 0xffffffffL);
    }

    private static float f(int bits) { return Float.intBitsToFloat(bits); }
    private static double d(int high, int low) { return Double.longBitsToDouble(join(high, low)); }
    private static int fr(float value) { return Float.floatToRawIntBits(value); }
    private static long dr(double value) { return Double.doubleToRawLongBits(value); }

    public static int partialFloat(int outer) {
        float[][] values = new float[outer][];
        return values.length * 31 + (outer == 0 || values[outer - 1] == null ? 1 : 2);
    }

    public static int fullFloat(int bits) {
        float[][] values = new float[2][2];
        values[1][0] = f(bits);
        return fr(values[1][0]);
    }

    private static long fullDoubleBits(int high, int low) {
        double[][] values = new double[2][2];
        values[1][1] = d(high, low);
        return dr(values[1][1]);
    }

    public static int fullDoubleHigh(int high, int low) {
        return (int) (fullDoubleBits(high, low) >>> 32);
    }

    public static int fullDoubleLow(int high, int low) {
        return (int) fullDoubleBits(high, low);
    }

    public static int distinctFloatRows(int bits) {
        float[][] values = new float[2][1];
        values[0][0] = f(bits);
        return fr(values[1][0]) + (values[0] == values[1] ? 100 : 200);
    }

    public static int partialDoubleCube(int outer, int middle) {
        double[][][] values = new double[outer][middle][];
        if (outer == 0) return 17;
        return values.length * 100 + values[0].length * 10 + (values[0][0] == null ? 1 : 2);
    }

    private static long fullDoubleCubeBits(int high, int low) {
        double[][][] values = new double[2][2][2];
        values[1][0][1] = d(high, low);
        return dr(values[1][0][1]);
    }

    public static int fullDoubleCubeHigh(int high, int low) {
        return (int) (fullDoubleCubeBits(high, low) >>> 32);
    }

    public static int fullDoubleCubeLow(int high, int low) {
        return (int) fullDoubleCubeBits(high, low);
    }

    public static int jaggedFloatAlias(int bits) {
        float[][] values = new float[3][];
        values[0] = new float[0];
        values[1] = new float[] { f(bits) };
        values[2] = values[1];
        return fr(values[2][0]) ^ (values[1] == values[2] ? 0 : 1);
    }

    public static int floatArrayMarkers(int seed) {
        Object value = new float[] { f(seed) };
        int result = value instanceof Object ? 1 : 0;
        result = result * 2 + (value instanceof Cloneable ? 1 : 0);
        result = result * 2 + (value instanceof java.io.Serializable ? 1 : 0);
        result = result * 2 + (value instanceof Object[] ? 1 : 0);
        return result;
    }

    public static int doubleMatrixMarkers(int seed) {
        Object value = new double[1][1];
        int result = value instanceof Object[] ? 1 : 0;
        result = result * 2 + (value instanceof Cloneable[] ? 1 : 0);
        result = result * 2 + (value instanceof java.io.Serializable[] ? 1 : 0);
        result = result * 2 + (value instanceof double[][] ? 1 : 0);
        result = result * 2 + (value instanceof long[][] ? 1 : 0);
        return result * 31 + seed;
    }

    public static int primitiveLeafIdentity(int seed) {
        Object f = new float[1];
        Object d = new double[1];
        int result = f instanceof int[] ? 1 : 0;
        result = result * 2 + (f instanceof double[] ? 1 : 0);
        result = result * 2 + (d instanceof long[] ? 1 : 0);
        result = result * 2 + (d instanceof float[] ? 1 : 0);
        return result * 31 + seed;
    }

    public static int castFloatIdentity(int bits) {
        float[] values = new float[] { f(bits) };
        Object object = values;
        float[] cast = (float[]) object;
        return fr(cast[0]) ^ (cast == values ? 0 : 1);
    }

    private static long castDoubleIdentityBits(int high, int low) {
        double[] values = new double[] { d(high, low) };
        Object object = values;
        double[] cast = (double[]) object;
        return dr(cast[0]) ^ (cast == values ? 0L : 1L);
    }

    public static int castDoubleIdentityHigh(int high, int low) {
        return (int) (castDoubleIdentityBits(high, low) >>> 32);
    }

    public static int castDoubleIdentityLow(int high, int low) {
        return (int) castDoubleIdentityBits(high, low);
    }

    public static int compatibleFloatRowStore(int bits) {
        float[][] values = new float[1][];
        Object[] widened = values;
        float[] row = new float[] { f(bits) };
        widened[0] = row;
        return fr(values[0][0]) ^ (values[0] == row ? 0 : 1);
    }

    private static long compatibleDoubleRowBits(int high, int low) {
        double[][] values = new double[1][];
        Object[] widened = values;
        double[] row = new double[] { d(high, low) };
        widened[0] = row;
        return dr(values[0][0]) ^ (values[0] == row ? 0L : 1L);
    }

    public static int compatibleDoubleRowHigh(int high, int low) {
        return (int) (compatibleDoubleRowBits(high, low) >>> 32);
    }

    public static int compatibleDoubleRowLow(int high, int low) {
        return (int) compatibleDoubleRowBits(high, low);
    }

    public static int nullRowStore(int seed) {
        float[][] values = new float[1][1];
        Object[] widened = values;
        widened[0] = null;
        return values[0] == null ? seed + 501 : seed + 601;
    }

    public static int incompatibleFloatRowStore(int seed) {
        float[][] values = new float[1][];
        Object[] widened = values;
        widened[0] = new double[] { seed };
        return seed;
    }

    public static int incompatibleDoubleHigherStore(int seed) {
        double[][][] values = new double[1][][];
        Object[][] widened = values;
        widened[0] = new float[][] { new float[] { seed } };
        return seed;
    }

    public static int castIntArrayToFloat(int seed) {
        Object value = new int[] { seed };
        return fr(((float[]) value)[0]);
    }

    public static int castFloatMatrixToDouble(int seed) {
        Object value = new float[][] { new float[] { seed } };
        return (int) dr(((double[][]) value)[0][0]);
    }

    public static int negativeFloatOuter(int outer) {
        return new float[outer][2].length;
    }

    public static int negativeDoubleInner(int outer, int inner) {
        return new double[outer][inner].length;
    }

    public static int dimensionsLeftToRight(int first, int second) {
        DimensionTrace.trace = 0;
        float[][] values = new float[DimensionTrace.count(first, 1)][DimensionTrace.count(second, 2)];
        return DimensionTrace.trace * 100 + values.length * 10 + (values.length == 0 ? 0 : values[0].length);
    }
}

class DimensionTrace {
    static int trace;

    static int count(int value, int digit) {
        trace = trace * 10 + digit;
        return value;
    }
}
