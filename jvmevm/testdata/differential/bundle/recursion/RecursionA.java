package bundle.recursion;

public class RecursionA {
    public static int sum(int value) {
        if (value <= 0) {
            return 0;
        }
        return value + RecursionB.sum(value - 1);
    }

    public static int parity(int value) {
        if (value == 0) {
            return 1;
        }
        return RecursionB.parity(value - 1);
    }

    public static int carry(int value, int depth) {
        int saved = value;
        if (depth == 0) {
            return saved;
        }
        return saved + RecursionB.carry(value + 3, depth - 1);
    }

    public static int forever(int value) {
        return RecursionB.forever(value + 1);
    }
}
