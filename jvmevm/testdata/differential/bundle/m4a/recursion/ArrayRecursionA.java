package bundle.m4a.recursion;

public class ArrayRecursionA {
    public static void fill(int[] values, int index, int seed) {
        if (index >= values.length) {
            return;
        }
        values[index] = seed + index;
        ArrayRecursionB.fill(values, index + 1, seed);
    }

    public static int sum(int[] values, int index) {
        if (index >= values.length) {
            return 0;
        }
        return values[index] + ArrayRecursionB.sum(values, index + 1);
    }
}
