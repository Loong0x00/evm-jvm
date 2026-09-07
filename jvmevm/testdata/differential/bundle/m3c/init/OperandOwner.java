package bundle.m3c.init;

public class OperandOwner {
    public static int value = initialize();
    public static int runs;

    private static int initialize() {
        runs++;
        return 41;
    }

    public static int combine(int first, int second) {
        return first * 10 + second + value + runs;
    }
}
