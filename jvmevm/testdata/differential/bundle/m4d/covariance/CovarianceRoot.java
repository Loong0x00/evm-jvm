package bundle.m4d.covariance;

/** Recursive array covariance, casts, type tests, and immutable actual component types. */
public class CovarianceRoot {
    public static int childArrayToBase(int value) {
        CovBase[] values = new CovChild[1];
        values[0] = new CovChild(value);
        return values[0].read();
    }

    public static int childArrayToObjectArray(int value) {
        CovChild[] children = new CovChild[1];
        Object[] values = children;
        values[0] = new CovGrand(value);
        return children[0].read();
    }

    public static int baseArrayAcceptsChild(int value) {
        CovBase[] values = new CovBase[2];
        values[0] = new CovBase(value);
        values[1] = new CovChild(value);
        return values[0].read() + values[1].read();
    }

    public static int actualChildStoreChild(int value) {
        Object[] values = new CovChild[1];
        values[0] = new CovChild(value);
        return ((CovChild[]) values)[0].read();
    }

    public static int actualChildStoreGrand(int value) {
        CovBase[] values = new CovChild[1];
        values[0] = new CovGrand(value);
        return values[0].read();
    }

    public static int childArrayInstanceChild(int value) {
        Object values = new CovChild[1];
        return values instanceof CovChild[] ? value : -1;
    }

    public static int childArrayInstanceBase(int value) {
        Object values = new CovChild[1];
        return values instanceof CovBase[] ? value : -1;
    }

    public static int childArrayInstanceObjectArray(int value) {
        Object values = new CovChild[1];
        return values instanceof Object[] ? value : -1;
    }

    public static int childArrayInstanceObject(int value) {
        Object values = new CovChild[1];
        return values instanceof Object ? value : -1;
    }

    public static int baseArrayNotChild(int value) {
        Object values = new CovBase[1];
        return values instanceof CovChild[] ? -1 : value;
    }

    public static int siblingArrayNotChild(int value) {
        Object values = new CovSibling[1];
        return values instanceof CovChild[] ? -1 : value;
    }

    public static int intArrayNotObjectArray(int value) {
        Object values = new int[1];
        return values instanceof Object[] ? -1 : value;
    }

    public static int intArrayIsObject(int value) {
        Object values = new int[1];
        return values instanceof Object ? value : -1;
    }

    public static int intMatrixIsObjectArray(int value) {
        Object values = new int[1][];
        return values instanceof Object[] ? value : -1;
    }

    public static int intMatrixNotObjectMatrix(int value) {
        Object values = new int[1][];
        return values instanceof Object[][] ? -1 : value;
    }

    public static int childMatrixToBaseMatrix(int value) {
        CovChild[][] children = new CovChild[1][];
        children[0] = new CovChild[1];
        CovBase[][] values = children;
        values[0][0] = new CovChild(value);
        return children[0][0].read();
    }

    public static int childMatrixToObjectMatrix(int value) {
        CovChild[][] children = new CovChild[1][];
        children[0] = new CovChild[1];
        Object[][] values = children;
        values[0][0] = new CovGrand(value);
        return children[0][0].read();
    }

    public static int childMatrixToObjectArray(int value) {
        CovChild[][] children = new CovChild[1][];
        Object[] values = children;
        CovChild[] row = new CovChild[1];
        row[0] = new CovChild(value);
        values[0] = row;
        return children[0][0].read();
    }

    public static int childMatrixInstanceBaseMatrix(int value) {
        Object values = new CovChild[1][];
        return values instanceof CovBase[][] ? value : -1;
    }

    public static int childMatrixInstanceObjectMatrix(int value) {
        Object values = new CovChild[1][];
        return values instanceof Object[][] ? value : -1;
    }

    public static int childArrayNotBaseMatrix(int value) {
        Object values = new CovChild[1];
        return values instanceof CovBase[][] ? -1 : value;
    }

    public static int intMatrixCastObjectArrayIdentity(int value) {
        int[][] matrix = new int[1][];
        matrix[0] = new int[1];
        Object object = matrix;
        Object[] values = (Object[]) object;
        ((int[]) values[0])[0] = value;
        return values == matrix ? matrix[0][0] : -1;
    }

    public static int childMatrixCastBaseIdentity(int value) {
        CovChild[][] matrix = new CovChild[1][];
        matrix[0] = new CovChild[1];
        Object object = matrix;
        CovBase[][] values = (CovBase[][]) object;
        values[0][0] = new CovChild(value);
        return values == matrix ? matrix[0][0].read() : -1;
    }

    public static int nullRecursiveCast(int value) {
        Object object = null;
        CovChild[][][] values = (CovChild[][][]) object;
        return values == null ? value : -1;
    }

    public static int rankThreeCovariance(int value) {
        CovChild[][][] cube = new CovChild[1][][];
        cube[0] = new CovChild[1][];
        cube[0][0] = new CovChild[1];
        CovBase[][][] widened = cube;
        widened[0][0][0] = new CovGrand(value);
        return cube[0][0][0].read();
    }

    public static int rankThreeTypeTest(int value) {
        Object cube = new CovChild[1][][];
        return cube instanceof CovBase[][][] && cube instanceof Object[][][] ? value : -1;
    }

    public static int primitiveRankDifference(int value) {
        Object matrix = new int[1][];
        return matrix instanceof int[][] && !(matrix instanceof int[]) ? value : -1;
    }

    public static int referenceRankDifference(int value) {
        Object matrix = new CovChild[1][];
        return matrix instanceof CovBase[][] && !(matrix instanceof CovBase[]) ? value : -1;
    }
}

class CovBase {
    int value;
    CovBase(int value) { this.value = value; }
    int read() { return value + 1; }
}

class CovChild extends CovBase {
    CovChild(int value) { super(value); }
    int read() { return value + 10; }
}

class CovGrand extends CovChild {
    CovGrand(int value) { super(value); }
    int read() { return value + 100; }
}

class CovSibling extends CovBase {
    CovSibling(int value) { super(value); }
}
