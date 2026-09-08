package bundle.m4e.covariance;

/** Covariance, recursive array type checks, casts, and stores on multianewarray results. */
public class CovarianceRoot {
    public static int childMatrixDefaults(int value) {
        CovChild[][] values = new CovChild[2][2];
        return values[0][0] == null && values[1][1] == null ? value : -1;
    }

    public static int childMatrixToBase(int value) {
        CovChild[][] children = new CovChild[2][1];
        CovBase[][] values = children;
        values[1][0] = new CovGrand(value);
        return children[1][0].read();
    }

    public static int childMatrixToObjectArray(int value) {
        CovChild[][] children = new CovChild[1][2];
        Object[] outer = children;
        ((CovChild[]) outer[0])[1] = new CovChild(value);
        return children[0][1].read();
    }

    public static int childCubeToBase(int value) {
        CovChild[][][] children = new CovChild[1][2][1];
        CovBase[][][] values = children;
        values[0][1][0] = new CovGrand(value);
        return children[0][1][0].read();
    }

    public static int childCubeTypeTests(int value) {
        Object values = new CovChild[1][1][1];
        return values instanceof CovChild[][][]
                && values instanceof CovBase[][][]
                && values instanceof Object[][][]
                && values instanceof Object[] ? value : -1;
    }

    public static int childMatrixCastIdentity(int value) {
        CovChild[][] children = new CovChild[1][1];
        Object object = children;
        CovBase[][] restored = (CovBase[][]) object;
        restored[0][0] = new CovChild(value);
        return restored == children ? children[0][0].read() : -1;
    }

    public static int primitiveCubeTypeTests(int value) {
        Object values = new int[1][1][1];
        return values instanceof int[][][]
                && values instanceof Object[][]
                && values instanceof Object[]
                && !(values instanceof Object[][][]) ? value : -1;
    }

    public static int primitiveCubeCastIdentity(int value) {
        int[][][] values = new int[1][1][2];
        Object[] outer = (Object[]) values;
        ((int[][]) outer[0])[0][1] = value;
        return outer == values ? values[0][0][1] : -1;
    }

    public static int partialChildCubeCovariance(int value) {
        CovChild[][][] children = new CovChild[2][1][];
        CovBase[][][] values = children;
        values[1][0] = new CovChild[1];
        values[1][0][0] = new CovGrand(value);
        return children[0][0] == null ? children[1][0][0].read() : -1;
    }

    public static int abstractComponentDefaults(int value) {
        CovAbstract[][] values = new CovAbstract[2][2];
        return values[0][0] == null && values[1][1] == null ? value : -1;
    }

    public static int validGrandStore(int value) {
        CovBase[][] values = new CovChild[1][1];
        values[0][0] = new CovGrand(value);
        return values[0][0].read();
    }

    public static int wrongOuterRowStore(int value) {
        CovChild[][] values = new CovChild[1][1];
        Object[] outer = values;
        outer[0] = new CovBase[value];
        return value;
    }

    public static int wrongLeafStore(int value) {
        CovBase[][] values = new CovChild[1][1];
        values[0][0] = new CovBase(value);
        return value;
    }

    public static int wrongCubePlaneStore(int value) {
        CovChild[][][] values = new CovChild[1][1][1];
        Object[] outer = values;
        outer[0] = new CovBase[1][value];
        return value;
    }

    public static int castPrimitiveCubeToObjectCube(int value) {
        Object values = new int[1][1][1];
        Object[][][] wrong = (Object[][][]) values;
        return wrong.length + value;
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

abstract class CovAbstract {
    abstract int read();
}
