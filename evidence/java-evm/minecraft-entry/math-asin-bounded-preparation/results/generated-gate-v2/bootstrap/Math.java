package java.lang;

/** Bounded Java 8 Math surface for the measured Minecraft startup path. */
public final class Math {
    private Math() {}

    public static int max(int a, int b) { if (a >= b) return a; return b; }
    public static int min(int a, int b) { if (a <= b) return a; return b; }

    public static native double sqrt(double value);
    public static native double sin(double value);
    public static native double asin(double value);
}
