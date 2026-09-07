package bundle.m3c.init;

public class ComputedFinalOwner {
    public static final int VALUE = compute();
    static int helperRuns;

    private static int compute() {
        helperRuns++;
        return 314;
    }
}
