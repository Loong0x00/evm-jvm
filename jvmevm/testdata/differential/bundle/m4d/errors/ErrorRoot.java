package bundle.m4d.errors;

/** Direct Java outcomes and aastore null/bounds/compatibility ordering. */
public class ErrorRoot {
    public static int negativeOrdinary(int length) {
        ErrorBase[] values = new ErrorBase[length];
        return values.length;
    }

    public static int negativeNested(int length) {
        int[][] values = new int[length][];
        return values.length;
    }

    public static int nullRead(int index) {
        ErrorBase[] values = null;
        return values[index].value;
    }

    public static int nullStoreIncompatible(int index) {
        Object[] values = null;
        values[index] = new ErrorBase();
        return index;
    }

    public static int nullStoreNegative(int index) {
        ErrorChild[] values = null;
        values[index] = null;
        return index;
    }

    public static int boundsReadNegative(int index) {
        ErrorBase[] values = new ErrorBase[1];
        return values[index] == null ? 1 : 0;
    }

    public static int boundsStoreEqual(int index) {
        ErrorBase[] values = new ErrorBase[1];
        values[index] = new ErrorBase();
        return index;
    }

    public static int boundsBeforeIncompatible(int index) {
        Object[] values = new ErrorChild[1];
        values[index] = new ErrorBase();
        return index;
    }

    public static int storeBaseIntoActualChild(int value) {
        ErrorBase[] widened = new ErrorChild[1];
        widened[0] = new ErrorBase();
        return value;
    }

    public static int storeSiblingIntoActualChild(int value) {
        Object[] widened = new ErrorChild[1];
        widened[0] = new ErrorSibling();
        return value;
    }

    public static int storeWrongNestedRow(int value) {
        Object[] widened = new ErrorChild[1][];
        widened[0] = new ErrorBase[1];
        return value;
    }

    public static int castIntMatrixToObjectMatrix(int value) {
        Object object = new int[1][];
        Object[][] values = (Object[][]) object;
        return values.length + value;
    }

    public static int castBaseArrayToChildArray(int value) {
        Object object = new ErrorBase[1];
        ErrorChild[] values = (ErrorChild[]) object;
        return values.length + value;
    }
}

class ErrorBase {
    int value;
}

class ErrorChild extends ErrorBase {
}

class ErrorSibling extends ErrorBase {
}
