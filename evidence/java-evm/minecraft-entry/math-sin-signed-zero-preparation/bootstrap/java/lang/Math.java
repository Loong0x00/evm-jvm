package java.lang;

/** Bounded Java 8 Math surface: int min/max, native sqrt, and signed-zero-only native sin. */
public final class Math {
    private Math() {}

    public static int max(int a, int b) { if (a >= b) return a; return b; }
    public static int min(int a, int b) { if (a <= b) return a; return b; }

    public static native double sqrt(double value);
    public static native double sin(double value);
}
