package bundle.isolation;

public class IsolationRoot {
    public static int leftRight(int first, int second) {
        return Alpha.apply(first) + Beta.apply(second);
    }

    public static int rightLeft(int first, int second) {
        return Beta.apply(first) - Alpha.apply(second);
    }

    public static int repeatedOwners(int value) {
        return Alpha.apply(value) + Beta.apply(value)
                + Alpha.apply(value + 1) + Beta.apply(value - 1);
    }

    public static int sameSignaturePairs(int first, int second) {
        return Alpha.pair(first, second) * 100 + Beta.pair(first, second);
    }
}
