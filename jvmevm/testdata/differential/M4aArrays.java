public final class M4aArrays {
    private M4aArrays() {}

    public static int zeroLength(int ignored) {
        int[] values = new int[0];
        return values.length;
    }

    public static int length(int size) {
        int[] values = new int[size];
        return values.length;
    }

    public static int zeroRead(int size, int index) {
        int[] values = new int[size];
        return values[index];
    }

    public static int writeRead(int size, int index, int value) {
        int[] values = new int[size];
        values[index] = value;
        return values[index];
    }

    public static int fillSum(int size, int seed) {
        int[] values = new int[size];
        for (int i = 0; i < values.length; i++) {
            values[i] = seed + i * 3;
        }
        return sum(values);
    }

    public static int search(int size, int target) {
        int[] values = new int[size];
        for (int i = 0; i < size; i++) {
            values[i] = i * 5 - 7;
        }
        return find(values, target);
    }

    public static int insertionSort(int a, int b, int c, int d) {
        int[] values = new int[4];
        values[0] = a;
        values[1] = b;
        values[2] = c;
        values[3] = d;
        for (int i = 1; i < values.length; i++) {
            int item = values[i];
            int j = i - 1;
            while (j >= 0 && values[j] > item) {
                values[j + 1] = values[j];
                j--;
            }
            values[j + 1] = item;
        }
        return values[0] * 1000 + values[1] * 100 + values[2] * 10 + values[3];
    }

    public static int bubbleSort(int a, int b, int c, int d) {
        int[] values = new int[4];
        values[0] = a;
        values[1] = b;
        values[2] = c;
        values[3] = d;
        for (int end = values.length - 1; end > 0; end--) {
            for (int i = 0; i < end; i++) {
                if (values[i] > values[i + 1]) {
                    int temporary = values[i];
                    values[i] = values[i + 1];
                    values[i + 1] = temporary;
                }
            }
        }
        return values[0] * 1000 + values[1] * 100 + values[2] * 10 + values[3];
    }

    public static int aliasWrite(int value) {
        int[] first = new int[1];
        int[] second = first;
        second[0] = value;
        return first[0];
    }

    public static int distinctWrite(int value) {
        int[] first = new int[1];
        int[] second = new int[1];
        second[0] = value;
        return first[0];
    }

    public static int aliasIdentity(int ignored) {
        int[] first = new int[0];
        int[] second = first;
        return first == second ? 1 : 0;
    }

    public static int distinctIdentity(int size) {
        int[] first = new int[size];
        int[] second = new int[size];
        return first != second ? 1 : 0;
    }

    public static int zeroLengthDistinct(int ignored) {
        int[] first = new int[0];
        int[] second = new int[0];
        return first == second ? 1 : 0;
    }

    public static int nullIdentity(int ignored) {
        int[] first = null;
        int[] second = null;
        return first == second ? 1 : 0;
    }

    public static int nullVsArray(int size) {
        int[] first = null;
        int[] second = new int[size];
        return first != second ? 1 : 0;
    }

    public static int localRoundTrip(int size, int value) {
        int[] first = new int[size];
        int[] second = first;
        int[] third = second;
        third[size - 1] = value;
        return first[size - 1];
    }

    public static int helperReturn(int size) {
        int[] values = make(size);
        return values.length;
    }

    public static int helperRoundTrip(int size, int index, int value) {
        int[] values = identity(make(size));
        set(values, index, value);
        return read(values, index);
    }

    public static int helperAlias(int value) {
        int[] first = make(1);
        int[] second = identity(first);
        set(second, 0, value);
        return read(first, 0);
    }

    public static int helperArgumentOrder(int left, int right) {
        int[] values = make(2);
        storePair(left, values, right);
        return values[0] * 10 + values[1];
    }

    public static int postIncrement(int initial) {
        int[] values = make(1);
        values[0] = initial;
        int old = values[0]++;
        return old * 100 + values[0];
    }

    public static int preIncrement(int initial) {
        int[] values = make(1);
        values[0] = initial;
        int updated = ++values[0];
        return updated * 100 + values[0];
    }

    public static int postIncrementExpression(int initial) {
        int[] values = make(1);
        values[0] = initial;
        return values[0]++ + values[0] * 10;
    }

    public static int preIncrementExpression(int initial) {
        int[] values = make(1);
        values[0] = initial;
        return ++values[0] + values[0] * 10;
    }

    public static int assignmentExpression(int index, int value) {
        int[] values = make(2);
        return (values[index] = value) + values[index];
    }

    public static int chainedAssignment(int value) {
        int[] values = make(2);
        values[0] = values[1] = value;
        return values[0] + values[1];
    }

    public static int compoundAssignment(int initial, int delta) {
        int[] values = make(1);
        values[0] = initial;
        return (values[0] += delta) + values[0];
    }

    public static int postIncrementAtComputedIndex(int index, int initial) {
        int[] values = make(3);
        values[index] = initial;
        int old = values[index]++;
        return old + values[index] * 10;
    }

    public static int recursiveSum(int size, int seed) {
        int[] values = make(size);
        fill(values, seed);
        return recursiveSumFrom(values, 0);
    }

    public static int reverseChecksum(int a, int b, int c) {
        int[] values = make(3);
        values[0] = a;
        values[1] = b;
        values[2] = c;
        reverse(values);
        return values[0] * 100 + values[1] * 10 + values[2];
    }

    public static int negativeAllocation(int size) {
        int[] values = new int[size];
        return values.length;
    }

    public static int nullLength(int ignored) {
        int[] values = null;
        return values.length;
    }

    public static int nullRead(int index) {
        int[] values = null;
        return values[index];
    }

    public static int nullWrite(int index, int value) {
        int[] values = null;
        values[index] = value;
        return value;
    }

    public static int readBounds(int size, int index) {
        int[] values = new int[size];
        return values[index];
    }

    public static int writeBounds(int size, int index, int value) {
        int[] values = new int[size];
        values[index] = value;
        return value;
    }

    private static int[] make(int size) {
        return new int[size];
    }

    private static int[] identity(int[] values) {
        return values;
    }

    private static void set(int[] values, int index, int value) {
        values[index] = value;
    }

    private static int read(int[] values, int index) {
        return values[index];
    }

    private static void storePair(int left, int[] values, int right) {
        values[0] = left;
        values[1] = right;
    }

    private static void fill(int[] values, int seed) {
        for (int i = 0; i < values.length; i++) {
            values[i] = seed + i;
        }
    }

    private static int sum(int[] values) {
        int result = 0;
        for (int i = 0; i < values.length; i++) {
            result += values[i];
        }
        return result;
    }

    private static int find(int[] values, int target) {
        for (int i = 0; i < values.length; i++) {
            if (values[i] == target) {
                return i;
            }
        }
        return -1;
    }

    private static int recursiveSumFrom(int[] values, int index) {
        if (index == values.length) {
            return 0;
        }
        return values[index] + recursiveSumFrom(values, index + 1);
    }

    private static void reverse(int[] values) {
        int left = 0;
        int right = values.length - 1;
        while (left < right) {
            int temporary = values[left];
            values[left] = values[right];
            values[right] = temporary;
            left++;
            right--;
        }
    }
}
