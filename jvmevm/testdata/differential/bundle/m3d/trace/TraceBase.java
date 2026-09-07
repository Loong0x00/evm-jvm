package bundle.m3d.trace;

public class TraceBase {
    public static int trace = start();

    private static int start() {
        return 1;
    }

    protected static int append(int digit) {
        trace = trace * 10 + digit;
        return trace;
    }
}
