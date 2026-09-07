package bundle.m3d.shared;

public class SharedBase {
    public static int counter = 10;

    public static int read(int bias) {
        return counter + bias;
    }

    public static void add(int amount) {
        counter = counter + amount;
    }
}
