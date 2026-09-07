package bundle.recursion;

public class RecursionB {
    public static int sum(int value) {
        if (value <= 0) {
            return 0;
        }
        return value + RecursionA.sum(value - 1);
    }

    public static int parity(int value) {
        if (value == 0) {
            return 0;
        }
        return RecursionA.parity(value - 1);
    }

    public static int carry(int value, int depth) {
        int saved = value * 2;
        if (depth == 0) {
            return saved;
        }
        return saved + RecursionA.carry(value + 3, depth - 1);
    }

    public static int forever(int value) {
        return RecursionA.forever(value + 1);
    }
}
