package bundle.m4a.init;

public class InitMaker {
    static int calls;

    public static int[] build(int size, int seed) {
        calls++;
        int[] values = new int[size];
        for (int i = 0; i < values.length; i++) {
            values[i] = seed + i;
        }
        return values;
    }
}
