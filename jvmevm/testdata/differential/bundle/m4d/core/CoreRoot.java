package bundle.m4d.core;

/** Basic reference-array allocation, storage, identity, and manually built nesting. */
public class CoreRoot {
    public static int zeroLength(int value) {
        CoreCell[] cells = new CoreCell[0];
        return cells.length == 0 ? value : -1;
    }

    public static int requestedLength(int length) {
        CoreCell[] cells = new CoreCell[length];
        return cells.length;
    }

    public static int defaultNull(int value) {
        CoreCell[] cells = new CoreCell[3];
        return cells[0] == null && cells[2] == null ? value : -1;
    }

    public static int storeLoad(int value) {
        CoreCell[] cells = new CoreCell[2];
        cells[1] = new CoreCell(value);
        return cells[1].value;
    }

    public static int storeNull(int value) {
        CoreCell[] cells = new CoreCell[1];
        cells[0] = new CoreCell(value);
        cells[0] = null;
        return cells[0] == null ? value : -1;
    }

    public static int aliasWrite(int value) {
        CoreCell[] cells = new CoreCell[1];
        CoreCell[] alias = cells;
        alias[0] = new CoreCell(value);
        return cells[0].value;
    }

    public static int distinctAllocations(int value) {
        CoreCell[] first = new CoreCell[1];
        CoreCell[] second = new CoreCell[1];
        first[0] = new CoreCell(value);
        return first != second && second[0] == null ? first[0].value : -1;
    }

    public static int distinctZeroAllocations(int value) {
        CoreCell[] first = new CoreCell[0];
        CoreCell[] second = new CoreCell[0];
        return first != second ? value : -1;
    }

    public static int identityThroughObject(int value) {
        CoreCell[] cells = new CoreCell[1];
        Object object = cells;
        CoreCell[] restored = (CoreCell[]) object;
        restored[0] = new CoreCell(value);
        return restored == cells ? cells[0].value : -1;
    }

    public static int objectArrayClassValue(int value) {
        Object[] values = new Object[2];
        values[0] = new CoreCell(value);
        return ((CoreCell) values[0]).value;
    }

    public static int objectArrayIntArray(int value) {
        Object[] values = new Object[2];
        int[] numbers = new int[1];
        numbers[0] = value;
        values[1] = numbers;
        return ((int[]) values[1])[0];
    }

    public static int heterogeneousObjectArray(int value) {
        Object[] values = new Object[4];
        values[0] = new CoreCell(value);
        values[1] = new int[2];
        values[2] = new CoreCell[1];
        values[3] = null;
        ((int[]) values[1])[1] = value + 1;
        ((CoreCell[]) values[2])[0] = (CoreCell) values[0];
        return ((CoreCell[]) values[2])[0].value + ((int[]) values[1])[1];
    }

    public static int objectArrayAlias(int value) {
        Object[] values = new Object[1];
        Object[] alias = values;
        alias[0] = new CoreCell(value);
        return ((CoreCell) values[0]).value;
    }

    public static int intMatrixOuterDefaults(int value) {
        int[][] matrix = new int[3][];
        return matrix.length == 3 && matrix[0] == null && matrix[2] == null ? value : -1;
    }

    public static int intMatrixRows(int value) {
        int[][] matrix = new int[2][];
        matrix[0] = new int[1];
        matrix[1] = new int[2];
        matrix[0][0] = value;
        matrix[1][1] = value + 2;
        return matrix[0][0] + matrix[1][1];
    }

    public static int intMatrixAliasedRows(int value) {
        int[][] matrix = new int[2][];
        int[] row = new int[1];
        matrix[0] = row;
        matrix[1] = row;
        matrix[0][0] = value;
        return matrix[1][0];
    }

    public static int intMatrixDistinctRows(int value) {
        int[][] matrix = new int[2][];
        matrix[0] = new int[1];
        matrix[1] = new int[1];
        matrix[0][0] = value;
        return matrix[0] != matrix[1] && matrix[1][0] == 0 ? matrix[0][0] : -1;
    }

    public static int referenceMatrixRows(int value) {
        CoreCell[][] matrix = new CoreCell[2][];
        matrix[0] = new CoreCell[1];
        matrix[1] = new CoreCell[2];
        matrix[1][1] = new CoreCell(value);
        return matrix[0][0] == null ? matrix[1][1].value : -1;
    }

    public static int referenceMatrixAlias(int value) {
        CoreCell[][] matrix = new CoreCell[2][];
        CoreCell[] row = new CoreCell[1];
        matrix[0] = row;
        matrix[1] = row;
        matrix[0][0] = new CoreCell(value);
        return matrix[1][0].value;
    }

    public static int nestedArrayInObjectArray(int value) {
        Object[] values = new Object[1];
        CoreCell[][] matrix = new CoreCell[1][];
        matrix[0] = new CoreCell[1];
        matrix[0][0] = new CoreCell(value);
        values[0] = matrix;
        return ((CoreCell[][]) values[0])[0][0].value;
    }

    public static int threeRanksManual(int value) {
        CoreCell[][][] cube = new CoreCell[1][][];
        cube[0] = new CoreCell[1][];
        cube[0][0] = new CoreCell[1];
        cube[0][0][0] = new CoreCell(value);
        return cube[0][0][0].value;
    }

    public static int arrayLengthThroughObject(int value) {
        Object object = new CoreCell[2];
        CoreCell[] cells = (CoreCell[]) object;
        return cells.length == 2 ? value : -1;
    }

    public static int sameElementIdentity(int value) {
        CoreCell cell = new CoreCell(value);
        CoreCell[] cells = new CoreCell[2];
        cells[0] = cell;
        cells[1] = cell;
        return cells[0] == cells[1] ? cells[0].value : -1;
    }

    public static int replaceElement(int value) {
        CoreCell[] cells = new CoreCell[1];
        CoreCell first = new CoreCell(value);
        CoreCell second = new CoreCell(value + 3);
        cells[0] = first;
        cells[0] = second;
        return cells[0] == second && cells[0] != first ? cells[0].value : -1;
    }

    public static int abstractComponentZero(int value) {
        CoreAbstract[] values = new CoreAbstract[0];
        return values.length == 0 ? value : -1;
    }

    public static int abstractComponentDefaults(int value) {
        CoreAbstract[] values = new CoreAbstract[2];
        return values[0] == null && values[1] == null ? value : -1;
    }
}

class CoreCell {
    int value;
    CoreCell(int value) { this.value = value; }
}

abstract class CoreAbstract {
    int value;
    abstract int read();
}
