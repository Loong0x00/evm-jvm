public class IntegerShifts {
    public static int shiftLeft(int value, int distance) {
        return value << distance;
    }

    public static int shiftRight(int value, int distance) {
        return value >> distance;
    }

    public static int shiftRightUnsigned(int value, int distance) {
        return value >>> distance;
    }
}
