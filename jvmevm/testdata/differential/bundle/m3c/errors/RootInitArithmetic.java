package bundle.m3c.errors;

public class RootInitArithmetic {
    static int value = 100 / zero();

    private static int zero() {
        return 0;
    }

    public static int entry(int input) {
        return value + input;
    }
}
