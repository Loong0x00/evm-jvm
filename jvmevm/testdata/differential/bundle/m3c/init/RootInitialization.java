package bundle.m3c.init;

public class RootInitialization {
    static int base = initializeBase();
    static int preparedDefault;

    private static int initializeBase() {
        preparedDefault = 6;
        return 40;
    }

    public static int rootArgumentsPreserved(int first, int second) {
        return first * 1000 + second * 10 + base + preparedDefault;
    }

    public static int rootInitializedValue(int addend) {
        return base + preparedDefault + addend;
    }
}
