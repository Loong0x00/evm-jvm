package bundle.m3c.errors;

public class HelperFailureRoot {
    static int value = initialize();

    private static int initialize() {
        return FailureMath.divide(17, 0);
    }

    public static int entry(int addend) {
        return value + addend;
    }
}
