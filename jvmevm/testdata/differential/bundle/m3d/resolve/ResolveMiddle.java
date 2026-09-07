package bundle.m3d.resolve;

public class ResolveMiddle extends ResolveBase {
    public static int value = 23;

    public static int selected(int input) {
        return input + 200;
    }

    public static int overloaded(int first, int second) {
        return first * 100 + second;
    }
}
