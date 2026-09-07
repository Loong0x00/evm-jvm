package bundle.m3c.lazy;

public class UnusedFailure {
    public static int mustNotRun = 1 / zero();

    private static int zero() {
        return 0;
    }
}
