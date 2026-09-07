public class M3aStaticCalls {
    private static int assemble3(int first, int second, int third) {
        return first * 10000 + second * 100 + third;
    }

    private static int zeroValue() {
        return 314159;
    }

    private static int privateTransform(int value) {
        return value * 9 - 4;
    }

    private static int overloaded(int value) {
        return value + 11;
    }

    private static int overloaded(int first, int second) {
        return first * 17 - second * 5;
    }

    private static int overloaded(int first, int second, int third) {
        return first + second * 10 + third * 100;
    }

    private static int leaf(int value) {
        return value * 3 + 1;
    }

    private static int middle(int value) {
        return leaf(value - 2) + 5;
    }

    private static int outer(int value) {
        return middle(value + 4) * 2;
    }

    private static int mix6(int first, int second, int third, int fourth,
                            int fifth, int sixth) {
        return first - second * 2 + third * 3 - fourth * 4
                + fifth * 5 - sixth * 6;
    }

    private static int divide(int dividend, int divisor) {
        return dividend / divisor;
    }

    private static int remainder(int dividend, int divisor) {
        return dividend % divisor;
    }

    private static int divideThrough(int dividend, int divisor) {
        return divide(dividend, divisor);
    }

    public static int multiArgumentOrder(int first, int second, int third) {
        return assemble3(first, second, third);
    }

    public static int multiArgumentPermutation(int first, int second, int third) {
        return assemble3(third, first, second);
    }

    public static int zeroArgumentCall(int prefix) {
        return prefix + zeroValue();
    }

    public static int zeroOnly() {
        return zeroValue();
    }

    public static int privateHelperCall(int value) {
        return privateTransform(value);
    }

    public static int overloadOne(int value) {
        return overloaded(value);
    }

    public static int overloadTwo(int first, int second) {
        return overloaded(first, second);
    }

    public static int overloadThree(int first, int second, int third) {
        return overloaded(first, second, third);
    }

    public static int nestedCall(int value) {
        return middle(value);
    }

    public static int deepNestedCall(int value) {
        return outer(value);
    }

    public static int callerPrefix(int prefix, int first, int second) {
        return prefix * 1000 + overloaded(first, second) - 7;
    }

    public static int twoCallPrefix(int first, int second) {
        return privateTransform(first) + privateTransform(second);
    }

    public static int sixArguments(int first, int second, int third, int fourth,
                                   int fifth, int sixth) {
        return mix6(first, second, third, fourth, fifth, sixth);
    }

    public static int returnedArithmetic(int value) {
        return privateTransform(value) * 7 + 3;
    }

    public static int calleeDivide(int dividend, int divisor) {
        return divide(dividend, divisor);
    }

    public static int calleeRemainder(int dividend, int divisor) {
        return remainder(dividend, divisor);
    }

    public static int callThroughDivide(int dividend, int divisor) {
        return divideThrough(dividend, divisor);
    }
}
