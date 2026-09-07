package bundle.samepkg;

public class PackageRoot {
    public static int nonpublicClass(int value) {
        return PackageHelper.packageTransform(value);
    }

    public static int nonpublicClassProtected(int value) {
        return PackageHelper.protectedTransform(value);
    }

    public static int packageMethod(int first, int second) {
        return SamePackagePublic.packageMethod(first, second);
    }

    public static int protectedMethod(int value) {
        return SamePackagePublic.protectedMethod(value);
    }

    public static int samePackageChain(int value) {
        return PackageHelper.packageTransform(value)
                + SamePackagePublic.packageMethod(value, value - 1);
    }
}
