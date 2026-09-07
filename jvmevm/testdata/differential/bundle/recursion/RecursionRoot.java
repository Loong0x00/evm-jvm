package bundle.recursion;

public class RecursionRoot {
    public static int crossSum(int value) {
        return RecursionA.sum(value);
    }

    public static int crossParity(int value) {
        return RecursionA.parity(value);
    }

    public static int crossFrameIsolation(int value, int depth) {
        return RecursionA.carry(value, depth);
    }

    public static int crossStackOverflow(int value) {
        return RecursionA.forever(value);
    }
}
