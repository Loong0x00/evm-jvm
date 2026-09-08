package bundle.m5ba.init;

/** ArithmeticException escaping long-valued root class initialization must be wrapped. */
public class ArithmeticInitRoot {
    static long VALUE = 0x123456789abcdef0L / zero();
    private static long zero() { return 0L; }
    public static int entry(int value) { return (int) VALUE + value; }
}
