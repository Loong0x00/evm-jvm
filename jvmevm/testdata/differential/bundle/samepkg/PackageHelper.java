package bundle.samepkg;

class PackageHelper {
    static int packageTransform(int value) {
        return value * 9 - 4;
    }

    protected static int protectedTransform(int value) {
        return value * 5 + 12;
    }
}
