package bundle.state;

public class VoidHelper {
    private static void noOp() {
        return;
    }

    public static void consume(int value) {
        int local = value + 1;
        local = local * 2;
    }

    public static void nested(int value) {
        consume(value);
        noOp();
    }
}
