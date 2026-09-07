public class LocalsAndArithmetic {
    public static int subtract(int left, int right) {
        return left - right;
    }

    public static int store0(int first, int second) {
        first = second;
        return first;
    }

    public static int store1(int first, int second) {
        second = first;
        return second;
    }

    public static int store2(int first, int second, int third) {
        third = first + second;
        return third;
    }

    public static int store3(int first, int second, int third, int fourth) {
        fourth = first + second;
        return fourth + third;
    }

    public static int genericLocals(int first, int second, int third, int fourth) {
        int total = first + second;
        int expanded = total + third;
        return expanded + fourth;
    }

    public static int increment(int value) {
        value++;
        return value;
    }

    public static int decrement(int value) {
        value--;
        return value;
    }

    public static int increment127(int value) {
        value += 127;
        return value;
    }

    public static int decrement128(int value) {
        value -= 128;
        return value;
    }
}
