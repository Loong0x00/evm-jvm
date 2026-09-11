public final class BridgeAlpha {
    private static int twist(int x) {
        return (x * 5) ^ (x >>> 1);
    }
    public static int run(int n) {
        int acc = 3;
        for (int i = 0; i < n; i++) {
            if ((i & 1) == 0) acc += twist(i + 2);
            else acc -= twist(i - 1);
        }
        return acc;
    }
}
