package bundle.m4a.helpers;

public final class ArrayRoot {
    private ArrayRoot() {}

    public static int createAndSum(int size, int seed) {
        return ArrayLibrary.sum(ArrayLibrary.create(size, seed));
    }

    public static int crossClassAlias(int value) {
        int[] values = ArrayLibrary.create(1, 0);
        int[] alias = ArrayLibrary.identity(values);
        ArrayLibrary.write(alias, 0, value);
        return ArrayLibrary.read(values, 0);
    }

    public static int crossClassDistinct(int value) {
        int[] first = ArrayLibrary.create(1, 0);
        int[] second = ArrayLibrary.create(1, 0);
        ArrayLibrary.write(second, 0, value);
        return ArrayLibrary.read(first, 0);
    }

    public static int returnedIdentity(int size) {
        int[] values = ArrayLibrary.create(size, 3);
        return ArrayLibrary.identity(values) == values ? 1 : 0;
    }

    public static int returnedDistinct(int size) {
        int[] first = ArrayLibrary.create(size, 3);
        int[] second = ArrayLibrary.create(size, 3);
        return first != second ? 1 : 0;
    }

    public static int voidMutation(int index, int value) {
        int[] values = ArrayLibrary.create(3, 1);
        ArrayLibrary.write(values, index, value);
        return ArrayLibrary.sum(values);
    }

    public static int rotateChecksum(int a, int b, int c) {
        int[] values = new int[3];
        values[0] = a;
        values[1] = b;
        values[2] = c;
        ArrayLibrary.rotateLeft(values);
        return values[0] * 100 + values[1] * 10 + values[2];
    }

    public static int recursiveCrossSum(int size, int seed) {
        int[] values = ArrayLibrary.create(size, seed);
        return ArrayLibrary.recursiveSum(values, 0);
    }

    public static int nullCrossLength(int ignored) {
        int[] values = ArrayLibrary.identity(null);
        return values.length;
    }

    public static int crossReadBounds(int size, int index) {
        int[] values = ArrayLibrary.create(size, 0);
        return ArrayLibrary.read(values, index);
    }
}
