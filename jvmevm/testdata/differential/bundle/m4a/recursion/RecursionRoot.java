package bundle.m4a.recursion;

public final class RecursionRoot {
    private RecursionRoot() {}

    public static int mutualFillAndSum(int size, int seed) {
        int[] values = new int[size];
        ArrayRecursionA.fill(values, 0, seed);
        return ArrayRecursionA.sum(values, 0);
    }

    public static int startFromOtherClass(int size, int seed) {
        int[] values = new int[size];
        ArrayRecursionB.fill(values, 0, seed);
        return ArrayRecursionB.sum(values, 0);
    }

    public static int recursiveAlias(int size, int seed) {
        int[] values = new int[size];
        int[] alias = values;
        ArrayRecursionA.fill(alias, 0, seed);
        return ArrayRecursionB.sum(values, 0);
    }
}
