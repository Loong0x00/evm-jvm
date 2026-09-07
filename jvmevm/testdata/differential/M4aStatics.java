public final class M4aStatics {
    private static int[] storage;
    private static int[] first;
    private static int[] second;
    private static final int[] FINAL_VALUES = makeFinal();
    private static int initializationCount;

    private M4aStatics() {}

    public static int preparedNull(int ignored) {
        return storage == null ? 1 : 0;
    }

    public static int assignAndRead(int size, int index, int value) {
        storage = new int[size];
        storage[index] = value;
        return storage[index];
    }

    public static int localAlias(int value) {
        storage = new int[1];
        int[] local = storage;
        local[0] = value;
        return storage[0];
    }

    public static int staticAlias(int value) {
        first = new int[1];
        second = first;
        second[0] = value;
        return first[0];
    }

    public static int staticDistinct(int value) {
        first = new int[1];
        second = new int[1];
        second[0] = value;
        return first[0];
    }

    public static int staticIdentity(int ignored) {
        first = new int[0];
        second = first;
        return first == second ? 1 : 0;
    }

    public static int staticDistinctIdentity(int ignored) {
        first = new int[0];
        second = new int[0];
        return first != second ? 1 : 0;
    }

    public static int helperReturnedStatic(int size, int index, int value) {
        storage = new int[size];
        int[] returned = returnStorage();
        returned[index] = value;
        return storage[index];
    }

    public static int replaceReference(int value) {
        storage = new int[1];
        int[] old = storage;
        storage = new int[1];
        old[0] = value;
        return storage[0] - old[0];
    }

    public static int finalReferenceMutable(int index, int value) {
        FINAL_VALUES[index] = value;
        return FINAL_VALUES[index] + FINAL_VALUES.length;
    }

    public static int initializedValues(int index) {
        return FINAL_VALUES[index];
    }

    public static int initializerRanOnce(int value) {
        FINAL_VALUES[0] += value;
        return initializationCount * 100 + FINAL_VALUES[0];
    }

    private static int[] returnStorage() {
        return storage;
    }

    private static int[] makeFinal() {
        initializationCount++;
        int[] values = new int[3];
        values[0] = 4;
        values[1] = 5;
        values[2] = 6;
        return values;
    }
}
