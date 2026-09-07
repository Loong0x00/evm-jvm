package bundle.publicapi;

public class PublicMath {
    public static int transform(int value) {
        return value * 37 + 21;
    }

    public static int combine(int first, int second) {
        return first * 101 - second * 17;
    }
}
