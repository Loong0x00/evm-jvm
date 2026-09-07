package bundle.m3d.owner;

public class DeclaringBase {
    public static int runs;
    public static int value = initialize();

    private static int initialize() {
        runs = runs + 1;
        return 31;
    }

    public static int inheritedCall(int input) {
        return runs * 1000 + value * 10 + input;
    }

    public static void store(int input) {
        value = input;
    }
}
