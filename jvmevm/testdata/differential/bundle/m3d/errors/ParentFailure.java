package bundle.m3d.errors;

public class ParentFailure {
    static int parentStarted = 1;
    static int parentFailure = fail();

    private static int fail() {
        return 1 / zero();
    }

    private static int zero() {
        return 0;
    }
}
