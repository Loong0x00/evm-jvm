package bundle.m4a.init;

public class InitOwner {
    public static int[] NULL_VALUE;
    public static int[] VALUES = InitMaker.build(4, 7);
    public static int[] ALIAS = VALUES;
    public static final int[] FINAL_ALIAS = ALIAS;

    public static int[] values() {
        return VALUES;
    }
}
