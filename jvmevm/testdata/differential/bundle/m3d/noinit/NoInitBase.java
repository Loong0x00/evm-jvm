package bundle.m3d.noinit;

public class NoInitBase {
    public static int trace = initialize();

    private static int initialize() {
        return 4;
    }

    protected static int append(int digit) {
        trace = trace * 10 + digit;
        return trace;
    }
}
