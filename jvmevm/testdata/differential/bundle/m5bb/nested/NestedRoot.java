package bundle.m5bb.nested;

public class NestedRoot {
    private static int fold(long value) {
        return (int) (value ^ (value >>> 32));
    }

    public static int partialTwo(int outer) {
        long[][] values = new long[outer][];
        int result = values.length;
        for (int i = 0; i < values.length; i++) {
            result = result * 31 + (values[i] == null ? 1 : 2);
        }
        return result;
    }

    public static int fullTwo(int outer, int inner) {
        long[][] values = new long[outer][inner];
        if (outer > 0 && inner > 0) {
            values[outer - 1][inner - 1] = 0x123456789abcdef0L;
            return fold(values[outer - 1][inner - 1]) + values.length + values[0].length;
        }
        return values.length * 31 + (outer == 0 ? 0 : values[0].length);
    }

    public static int distinctRows(int seed) {
        long[][] values = new long[2][1];
        values[0][0] = seed;
        return fold(values[1][0]) + (values[0] == values[1] ? 100 : 200);
    }

    public static int partialThree(int outer, int middle) {
        long[][][] values = new long[outer][middle][];
        if (outer == 0) {
            return 17;
        }
        return values.length * 100 + values[0].length * 10 + (values[0][0] == null ? 1 : 2);
    }

    public static int fullThree(int seed) {
        long[][][] values = new long[2][2][2];
        values[1][0][1] = ((long) seed << 40) ^ 0x00000000abcdef01L;
        return fold(values[1][0][1]) + fold(values[0][1][1]) +
            (values[0] == values[1] ? 1000 : 2000);
    }

    public static int jaggedMutation(int seed) {
        long[][] values = new long[3][];
        values[0] = new long[0];
        values[1] = new long[] { seed };
        values[2] = values[1];
        values[2][0] += 0x100000001L;
        return fold(values[1][0]) + (values[1] == values[2] ? 31 : 47);
    }

    public static int longArrayMarkers(int seed) {
        Object value = new long[] { seed };
        int result = value instanceof Object ? 1 : 0;
        result = result * 2 + (value instanceof Cloneable ? 1 : 0);
        result = result * 2 + (value instanceof java.io.Serializable ? 1 : 0);
        result = result * 2 + (value instanceof Object[] ? 1 : 0);
        return result * 31 + seed;
    }

    public static int matrixMarkers(int seed) {
        Object value = new long[1][1];
        int result = value instanceof Object[] ? 1 : 0;
        result = result * 2 + (value instanceof Cloneable[] ? 1 : 0);
        result = result * 2 + (value instanceof java.io.Serializable[] ? 1 : 0);
        result = result * 2 + (value instanceof long[][] ? 1 : 0);
        result = result * 2 + (value instanceof int[][] ? 1 : 0);
        return result * 31 + seed;
    }

    public static int castLongIdentity(int seed) {
        long[] values = new long[] { ((long) seed << 32) | (seed & 0xffffffffL) };
        Object value = values;
        long[] cast = (long[]) value;
        return fold(cast[0]) + (cast == values ? 101 : 202);
    }

    public static int castMatrixIdentity(int seed) {
        long[][] values = new long[1][1];
        Object[] widened = values;
        long[][] cast = (long[][]) widened;
        cast[0][0] = seed;
        return fold(values[0][0]) + (cast == values ? 303 : 404);
    }

    public static int compatibleStore(int seed) {
        long[][] values = new long[1][];
        Object[] widened = values;
        long[] row = new long[] { 0x700000008L, seed };
        widened[0] = row;
        return fold(values[0][0] + values[0][1]) + (values[0] == row ? 17 : 29);
    }

    public static int nullStore(int seed) {
        long[][] values = new long[1][1];
        Object[] widened = values;
        widened[0] = null;
        return values[0] == null ? seed + 501 : seed + 601;
    }

    public static int incompatibleRowStore(int seed) {
        long[][] values = new long[1][];
        Object[] widened = values;
        widened[0] = new int[] { seed };
        return seed;
    }

    public static int incompatibleHigherStore(int seed) {
        long[][][] values = new long[1][][];
        Object[][] widened = values;
        widened[0] = new int[][] { new int[] { seed } };
        return seed;
    }

    public static int castIntArrayToLong(int seed) {
        Object value = new int[] { seed };
        return fold(((long[]) value)[0]);
    }

    public static int castIntMatrixToLong(int seed) {
        Object value = new int[][] { new int[] { seed } };
        return fold(((long[][]) value)[0][0]);
    }

    public static int negativeOuter(int outer) {
        return new long[outer][2].length;
    }

    public static int negativeInnerAfterZeroOuter(int outer, int inner) {
        return new long[outer][inner].length;
    }

    public static int nestedNullRead(int index) {
        long[][] values = new long[1][];
        return fold(values[0][index]);
    }

    public static int nestedBoundsWrite(int index) {
        long[][] values = new long[1][1];
        values[0][index] = Long.MAX_VALUE;
        return index;
    }

    public static int dimensionsLeftToRight(int first, int second) {
        DimensionTrace.trace = 0;
        long[][] values = new long[DimensionTrace.count(first, 1)][DimensionTrace.count(second, 2)];
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
