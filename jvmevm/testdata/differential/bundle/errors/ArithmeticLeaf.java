package bundle.errors;

public class ArithmeticLeaf {
    public static int divide(int dividend, int divisor) {
        return dividend / divisor;
    }

    public static int remainder(int dividend, int divisor) {
        return dividend % divisor;
    }

    public static void divideAndDiscard(int dividend, int divisor) {
        int quotient = dividend / divisor;
    }
}
