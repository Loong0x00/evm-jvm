package bundle.m3d.hidden;

class HiddenBase {
    public static int value = initialize();

    private static int initialize() {
        return 50;
    }

    public static int compute(int input) {
        return value * 10 + input;
    }

    public static void store(int input) {
        value = input;
    }
}
