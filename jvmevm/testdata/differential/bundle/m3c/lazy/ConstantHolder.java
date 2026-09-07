package bundle.m3c.lazy;

public class ConstantHolder {
    public static final int VALUE = 73;
    static int mustNotRun = 1 / zero();

    private static int zero() {
        return 0;
    }
}
