package java.lang;

/** Deliberately invalid as a replacement for the VM-owned Math image. */
public final class Math {
    private Math() {}
    public static double min(double a, double b) { return 0.0d; }
    public static double max(double a, double b) { return 0.0d; }
}
