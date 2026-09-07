public class M3aFrames {
    private static int alterLocals(int first, int second) {
        int originalFirst = first;
        first = second + 100;
        int scratch = originalFirst * 3;
        second = first - scratch;
        return second + scratch * 2;
    }

    private static int rewriteParameter(int value) {
        value = value * 5 + 1;
        return value;
    }

    private static void noOp() {
        return;
    }

    private static void consume(int value) {
        int local = value + 1;
        local = local * 2;
    }

    private static void nestedVoid(int value) {
        consume(value);
        noOp();
    }

    private static int ignoredResult(int value) {
        return value * 13 - 6;
    }

    private static int ignoredNested(int value) {
        return ignoredResult(value + 2);
    }

    private static int combine(int first, int second) {
        int local = first * 7;
        return local + second;
    }

    private static void divideAndDiscard(int dividend, int divisor) {
        int quotient = dividend / divisor;
    }

    public static int callerLocalIsolation(int first, int second) {
        int savedFirst = first;
        int savedSecond = second;
        int result = alterLocals(first, second);
        return savedFirst * 10000 + savedSecond * 100 + result;
    }

    public static int parameterIsolation(int value) {
        int result = rewriteParameter(value);
        return value * 100 + result;
    }

    public static int voidNoArgs(int value) {
        noOp();
        return value + 1;
    }

    public static int voidOne(int value) {
        consume(value);
        return value - 1;
    }

    public static int nestedVoidCall(int value) {
        nestedVoid(value);
        return value * 2;
    }

    public static int discardInt(int value) {
        ignoredResult(value);
        return value + 9;
    }

    public static int discardNested(int value) {
        ignoredNested(value);
        return value - 9;
    }

    public static int prefixAndCall(int prefix, int first, int second) {
        return prefix + combine(first, second);
    }

    public static int prefixAcrossTwoCalls(int first, int second) {
        return combine(first, second) - combine(second, first);
    }

    public static int voidDivide(int dividend, int divisor) {
        divideAndDiscard(dividend, divisor);
        return dividend + divisor;
    }
}
