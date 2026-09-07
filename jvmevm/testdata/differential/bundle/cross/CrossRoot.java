package bundle.cross;

import bundle.middle.PublicBridge;
import bundle.publicapi.PublicMath;

public class CrossRoot {
    public static int crossPackageDirect(int value) {
        return PublicMath.transform(value);
    }

    public static int crossPackageArguments(int first, int second) {
        return PublicMath.combine(first, second);
    }

    public static int crossPackageNested(int value) {
        return PublicBridge.nested(value);
    }

    public static int crossPackageCallerState(int prefix, int first, int second) {
        int saved = prefix;
        int result = PublicBridge.twoCalls(first, second);
        return saved * 1000 + result;
    }
}
