package bundle.m4a.helpers;

public class ArrayLibrary {
    public static int[] create(int size, int seed) {
        int[] values = new int[size];
        fill(values, seed);
        return values;
    }

    public static void fill(int[] values, int seed) {
        for (int i = 0; i < values.length; i++) {
            values[i] = seed + i * 2;
        }
    }

    public static int sum(int[] values) {
        int result = 0;
        for (int i = 0; i < values.length; i++) {
            result += values[i];
        }
        return result;
    }

    public static int[] identity(int[] values) {
        return values;
    }

    public static void write(int[] values, int index, int value) {
        values[index] = value;
    }

    public static int read(int[] values, int index) {
        return values[index];
    }

    public static void rotateLeft(int[] values) {
        if (values.length <= 1) {
            return;
        }
        int first = values[0];
        for (int i = 1; i < values.length; i++) {
            values[i - 1] = values[i];
        }
        values[values.length - 1] = first;
    }

    static int recursiveSum(int[] values, int index) {
        if (index == values.length) {
            return 0;
        }
        return values[index] + recursiveSum(values, index + 1);
    }
}
