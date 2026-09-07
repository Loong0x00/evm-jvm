package bundle.middle;

import bundle.publicapi.PublicMath;

public class PublicBridge {
    public static int nested(int value) {
        return PublicMath.transform(value + 2) - 8;
    }

    public static int twoCalls(int first, int second) {
        return PublicMath.combine(first, second) + PublicMath.transform(second);
    }
}
