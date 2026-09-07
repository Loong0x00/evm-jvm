package bundle.privatecall;

public class PrivatePartner {
    public static int external(int value) {
        return value * 7 - 3;
    }

    public static void consume(int value) {
        int local = value * 2;
        local = local + 1;
    }
}
