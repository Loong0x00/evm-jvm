package bundle.basic;

public class BasicHelper {
    private static int leaf(int value) {
        return value * 3 + 7;
    }

    public static int transform(int value) {
        return leaf(value) - 11;
    }

    public static int zero() {
        return 271828;
    }

    public static int combine(int first, int second, int third) {
        return first * 10000 + second * 100 + third;
    }

    public static int overloaded(int value) {
        return value + 19;
    }

    public static int overloaded(int first, int second) {
        return first * 13 - second * 7;
    }
}
