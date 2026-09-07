package bundle.errors;

public class ArithmeticRelay {
    public static int divide(int dividend, int divisor) {
        return ArithmeticLeaf.divide(dividend, divisor);
    }

    public static int remainder(int dividend, int divisor) {
        return ArithmeticLeaf.remainder(dividend, divisor);
    }

    public static void divideVoid(int dividend, int divisor) {
        ArithmeticLeaf.divideAndDiscard(dividend, divisor);
    }
}
