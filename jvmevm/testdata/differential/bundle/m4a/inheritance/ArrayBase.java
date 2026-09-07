package bundle.m4a.inheritance;

public class ArrayBase {
    public static int[] DATA = initialize();
    public static final int[] FINAL_DATA = new int[2];

    private static int[] initialize() {
        int[] values = new int[3];
        values[0] = 2;
        values[1] = 4;
        values[2] = 6;
        return values;
    }

    public static int[] data() {
        return DATA;
    }
}
