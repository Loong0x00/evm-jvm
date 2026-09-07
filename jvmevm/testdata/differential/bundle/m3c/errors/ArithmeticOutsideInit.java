package bundle.m3c.errors;

public class ArithmeticOutsideInit {
    static int initialized = 12;

    public static int divide(int dividend, int divisor) {
        return initialized + dividend / divisor;
    }
}
