package bundle.m4e.core;

/** Rectangular and partially allocated multidimensional arrays produced by multianewarray. */
public class CoreRoot {
    public static int int2Lengths(int rows, int columns) {
        int[][] values = new int[rows][columns];
        return values.length * 100 + values[0].length;
    }

    public static int int2Defaults(int value) {
        int[][] values = new int[2][3];
        return values[0][0] == 0 && values[1][2] == 0 ? value : -1;
    }

    public static int int2Write(int value) {
        int[][] values = new int[2][3];
        values[1][2] = value;
        return values[1][2];
    }

    public static int int3Lengths(int value) {
        int[][][] values = new int[2][3][4];
        return values.length * 100 + values[0].length * 10 + values[1][2].length + value;
    }

    public static int int3Defaults(int value) {
        int[][][] values = new int[2][2][2];
        return values[0][0][0] == 0 && values[1][1][1] == 0 ? value : -1;
    }

    public static int int3Write(int value) {
        int[][][] values = new int[2][2][3];
        values[1][0][2] = value;
        return values[1][0][2];
    }

    public static int int4Write(int value) {
        int[][][][] values = new int[1][2][2][2];
        values[0][1][0][1] = value;
        return values[0][1][0][1];
    }

    public static int reference2Defaults(int value) {
        CoreCell[][] values = new CoreCell[2][3];
        return values[0][0] == null && values[1][2] == null ? value : -1;
    }

    public static int reference2Write(int value) {
        CoreCell[][] values = new CoreCell[2][2];
        values[1][0] = new CoreCell(value);
        return values[1][0].read();
    }

    public static int reference3Defaults(int value) {
        CoreCell[][][] values = new CoreCell[2][1][2];
        return values[0][0][0] == null && values[1][0][1] == null ? value : -1;
    }

    public static int reference3Write(int value) {
        CoreCell[][][] values = new CoreCell[1][2][2];
        values[0][1][1] = new CoreCell(value);
        return values[0][1][1].read();
    }

    public static int zeroOuterInt(int value) {
        int[][] values = new int[0][3];
        return values.length == 0 ? value : -1;
    }

    public static int zeroOuterReference(int value) {
        CoreCell[][][] values = new CoreCell[0][2][3];
        return values.length == 0 ? value : -1;
    }

    public static int zeroInnerInt(int value) {
        int[][] values = new int[2][0];
        return values[0].length == 0 && values[1].length == 0 ? value : -1;
    }

    public static int zeroInnerReference(int value) {
        CoreCell[][] values = new CoreCell[2][0];
        return values[0].length == 0 && values[1].length == 0 ? value : -1;
    }

    public static int distinctEmptyChildren(int value) {
        int[][] values = new int[2][0];
        return values[0] != values[1] ? value : -1;
    }

    public static int zeroMiddleDistinct(int value) {
        int[][][] values = new int[2][0][3];
        return values[0] != values[1] && values[0].length == 0 && values[1].length == 0 ? value : -1;
    }

    public static int zeroDeepDistinct(int value) {
        CoreCell[][][] values = new CoreCell[2][2][0];
        return values[0] != values[1]
                && values[0][0] != values[0][1]
                && values[0][0] != values[1][0]
                && values[1][0].length == 0 ? value : -1;
    }

    public static int partialIntNullLeaves(int value) {
        int[][][] values = new int[2][3][];
        return values[0] != values[1] && values[0][0] == null && values[1][2] == null ? value : -1;
    }

    public static int partialReferenceNullLeaves(int value) {
        CoreCell[][][][] values = new CoreCell[2][1][][];
        return values[0] != values[1] && values[0][0] == null && values[1][0] == null ? value : -1;
    }

    public static int partialThenFill(int value) {
        int[][][] values = new int[2][2][];
        values[1][0] = new int[1];
        values[1][0][0] = value;
        return values[0][0] == null ? values[1][0][0] : -1;
    }

    public static int aliasGeneratedRows(int value) {
        int[][] values = new int[2][2];
        values[1] = values[0];
        values[0][1] = value;
        return values[1][1];
    }

    public static int mutateToJagged(int value) {
        int[][] values = new int[2][2];
        values[1] = new int[3];
        values[1][2] = value;
        return values[0].length * 10 + values[1].length + values[1][2];
    }

    public static int distinctGeneratedRows(int value) {
        CoreCell[][] values = new CoreCell[2][1];
        values[0][0] = new CoreCell(value);
        return values[0] != values[1] && values[1][0] == null ? values[0][0].read() : -1;
    }
}

class CoreCell {
    int value;
    CoreCell(int value) { this.value = value; }
    int read() { return value; }
}
