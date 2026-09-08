package bundle.m5ca.init;

/** A genuine switch executes while the selected root class is initializing. */
public class ArithmeticInitRoot {
    static int value = initialize();

    static int initialize() {
        int key = 3;
        switch (key) {
        case -1: return 11;
        case 0: return 22;
        case 3:
            int zero = key - 3;
            return 100 / zero;
        default: return 44;
        }
    }

    public static int entry(int seed) {
        return value + seed;
    }
}
