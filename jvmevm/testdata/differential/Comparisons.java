public class Comparisons {
    public static int equalZero(int value) {
        if (value == 0) return 1;
        return 0;
    }

    public static int notEqualZero(int value) {
        if (value != 0) return 1;
        return 0;
    }

    public static int lessThanZero(int value) {
        if (value < 0) return 1;
        return 0;
    }

    public static int greaterOrEqualZero(int value) {
        if (value >= 0) return 1;
        return 0;
    }

    public static int greaterThanZero(int value) {
        if (value > 0) return 1;
        return 0;
    }

    public static int lessOrEqualZero(int value) {
        if (value <= 0) return 1;
        return 0;
    }

    public static int equal(int left, int right) {
        if (left == right) return 1;
        return 0;
    }

    public static int notEqual(int left, int right) {
        if (left != right) return 1;
        return 0;
    }

    public static int lessThan(int left, int right) {
        if (left < right) return 1;
        return 0;
    }

    public static int greaterOrEqual(int left, int right) {
        if (left >= right) return 1;
        return 0;
    }

    public static int greaterThan(int left, int right) {
        if (left > right) return 1;
        return 0;
    }

    public static int lessOrEqual(int left, int right) {
        if (left <= right) return 1;
        return 0;
    }
}
