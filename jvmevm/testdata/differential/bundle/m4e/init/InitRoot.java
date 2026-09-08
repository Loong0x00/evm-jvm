package bundle.m4e.init;

/** Component lifecycle and class-initializer behavior around multianewarray. */
public class InitRoot {
    static int order;

    public static int componentNoInitialization(int value) {
        QuietComponent[][] values = new QuietComponent[2][2];
        return InitProbe.componentInitializations == 0 && values[1][1] == null ? value : -1;
    }

    public static int componentNoConstructor(int value) {
        QuietComponent[][] values = new QuietComponent[1][3];
        return InitProbe.constructions == 0 && values[0][2] == null ? value : -1;
    }

    public static int failingComponentNoInitialization(int value) {
        FailingComponent[][] values = new FailingComponent[2][1];
        return values[0][0] == null && values[1][0] == null ? value : -1;
    }

    public static int abstractComponentNoInitialization(int value) {
        QuietAbstract[][][] values = new QuietAbstract[1][2][1];
        return InitProbe.abstractInitializations == 0 && values[0][1][0] == null ? value : -1;
    }

    public static int partialComponentNoInitialization(int value) {
        QuietComponent[][][] values = new QuietComponent[2][1][];
        return InitProbe.componentInitializations == 0 && values[0][0] == null ? value : -1;
    }

    public static int initializerAllocatedLengths(int value) {
        return AllocatingHolder.values.length * 10 + AllocatingHolder.values[0].length + value;
    }

    public static int initializerAllocatedDefaults(int value) {
        return AllocatingHolder.values[0][0] == 0 && AllocatingHolder.values[1][2] == 0 ? value : -1;
    }

    public static int initializerReferenceDefaults(int value) {
        return AllocatingHolder.cells[0][0] == null && AllocatingHolder.cells[1][0] == null ? value : -1;
    }

    public static int dimensionEvaluationOrder(int first, int second) {
        order = 0;
        int[][] values = new int[firstCount(first)][secondCount(second)];
        return order * 100 + values.length * 10 + values[0].length;
    }

    public static int negativeOuter(int value) {
        int[][] values = new int[value][2];
        return values.length;
    }

    public static int negativeInner(int value) {
        int[][] values = new int[2][value];
        return values.length;
    }

    public static int zeroOuterNegativeInner(int value) {
        int[][] values = new int[0][value];
        return values.length;
    }

    public static int zeroMiddleNegativeDeep(int value) {
        int[][][] values = new int[2][0][value];
        return values.length;
    }

    public static int initializerNegative(int value) {
        return NegativeHolder.values.length + value;
    }

    private static int firstCount(int value) {
        order = order * 10 + 1;
        return value;
    }

    private static int secondCount(int value) {
        order = order * 10 + 2;
        return value;
    }
}

class InitProbe {
    static int componentInitializations;
    static int constructions;
    static int abstractInitializations;
}

class QuietComponent {
    static int marker = initialize();

    QuietComponent() {
        InitProbe.constructions++;
    }

    static int initialize() {
        InitProbe.componentInitializations++;
        return 1;
    }
}

class FailingComponent {
    static int marker = fail();

    static int fail() {
        int zero = 0;
        return 1 / zero;
    }
}

abstract class QuietAbstract {
    static int marker = initialize();

    static int initialize() {
        InitProbe.abstractInitializations++;
        return 1;
    }

    abstract int read();
}

class AllocatingHolder {
    static int[][] values = new int[2][3];
    static QuietComponent[][] cells = new QuietComponent[2][1];
}

class NegativeHolder {
    static int[][] values = new int[1][-1];
}
