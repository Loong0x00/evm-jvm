public final class BridgeBeta {
    private static int fold(int x, int i) {
        return (x + i * 7) ^ (i << 2);
    }
    public static int run(int n) {
        int acc = 11;
        int i = 0;
        while (i < n) {
            acc = fold(acc, i);
            if (acc < 0) acc = -acc + 9;
            else acc += (i & 3);
            i++;
        }
        return acc;
    }
}
