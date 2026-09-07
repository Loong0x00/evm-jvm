package bundle.m3d.resolve;

public class ResolveBase {
    public static int shared = 7;
    public static int value = 11;
    public static int initialized = initialize();

    private static int initialize() {
        return 31;
    }

    public static int selected(int input) {
        return input + 100;
    }

    public static int overloaded(int input) {
        return input * 3 + 1;
    }

    public static int overloaded(int first, int second) {
        return first * 10 + second;
    }
}
