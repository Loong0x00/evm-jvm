package bundle.errors;

public class ErrorRoot {
    public static int crossDivide(int dividend, int divisor) {
        return ArithmeticLeaf.divide(dividend, divisor);
    }

    public static int nestedDivide(int dividend, int divisor) {
        return ArithmeticRelay.divide(dividend, divisor);
    }

    public static int nestedRemainder(int dividend, int divisor) {
        return ArithmeticRelay.remainder(dividend, divisor);
    }

    public static int voidDivide(int dividend, int divisor) {
        ArithmeticRelay.divideVoid(dividend, divisor);
        return dividend + divisor;
    }
}
