package java.lang;

/** Bounded Java 8 Math surface: int min/max and deterministic native binary64 sqrt only. */
public final class Math {
    private Math() {}

    public static int max(int a, int b) { if (a >= b) return a; return b; }
    public static int min(int a, int b) { if (a <= b) return a; return b; }

    public static native double sqrt(double value);
    public static native double sin(double value);
}
