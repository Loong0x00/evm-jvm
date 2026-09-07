public class M3cStatics {
    static int defaultValue;
    static int initializedValue = 17;
    static int counter = 10;
    static int ceiling = 2147483647;
    static int floor = -2147483648;
    public static int publicValue = 31;
    private static int privateValue = -9;
    static final int COMPILED_CONSTANT = 1234567;
    static final int COMPUTED_FINAL = computeFinal();

    private static int computeFinal() {
        return 2718;
    }

    public static int readDefault(int addend) {
        return defaultValue + addend;
    }

    public static int writeThenRead(int value) {
        defaultValue = value;
        return defaultValue;
    }

    public static int postIncrement() {
        return counter++;
    }

    public static int postIncrementAndObserve() {
        int old = counter++;
        return old * 100 + counter;
    }

    public static int preIncrement() {
        return ++counter;
    }

    public static int incrementOverflow() {
        return ++ceiling;
    }

    public static int postIncrementOverflowState() {
        int old = ceiling++;
        return old + ceiling;
    }

    public static int postDecrementUnderflowState() {
        int old = floor--;
        return old + floor;
    }

    public static int readComputedFinal(int addend) {
        return COMPUTED_FINAL + addend;
    }

    public static int readCompiledConstant(int addend) {
        return COMPILED_CONSTANT + addend;
    }

    public static int accessLevels(int addend) {
        return publicValue + privateValue + initializedValue + addend;
    }

    public static int repeatedMutation(int value) {
        defaultValue = value;
        defaultValue++;
        defaultValue = defaultValue * 3;
        return defaultValue;
    }

    public static int freshResetProbe(int delta) {
        counter += delta;
        return counter;
    }
}
