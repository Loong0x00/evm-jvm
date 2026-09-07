package bundle.samepkg;

public class SamePackagePublic {
    static int packageMethod(int first, int second) {
        return first * 31 - second * 7;
    }

    protected static int protectedMethod(int value) {
        return value * 11 + 6;
    }
}
