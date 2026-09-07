package bundle.m3c.init;

public class OnceOwner {
    static int runs;
    static int value = initialize();

    private static int initialize() {
        runs++;
        return 70 + runs;
    }

    public static int readValue() {
        return value;
    }

    public static int readRuns() {
        return runs;
    }
}
