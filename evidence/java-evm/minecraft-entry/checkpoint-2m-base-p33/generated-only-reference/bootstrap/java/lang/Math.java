package java.lang;

/**
 * Bounded Java 8 Math image for the LOCAL Minecraft interpreter.
 * Existing int min/max and native sqrt/sin/asin/cos surfaces are preserved.
 */
public final class Math {
    private Math() {}

    public static int max(int a, int b) {
        if (a >= b) return a;
        return b;
    }

    public static int min(int a, int b) {
        if (a <= b) return a;
        return b;
    }

    public static native double sqrt(double a);
    public static native double sin(double a);
    public static native double asin(double a);
    public static native double cos(double a);

    /** Java 8 Math.min semantics, including first-NaN and negative zero. */
    public static double min(double a, double b) {
        if (a != a) return a;
        if (b != b) return b;
        if (a == 0.0d && b == 0.0d) {
            if (1.0d / a < 0.0d) return a;
            if (1.0d / b < 0.0d) return b;
            return a;
        }
        return a <= b ? a : b;
    }

    /** Java 8 Math.max semantics, including first-NaN and positive zero. */
    public static double max(double a, double b) {
        if (a != a) return a;
        if (b != b) return b;
        if (a == 0.0d && b == 0.0d) {
            if (1.0d / a > 0.0d) return a;
            if (1.0d / b > 0.0d) return b;
            return a;
        }
        return a >= b ? a : b;
    }
}
