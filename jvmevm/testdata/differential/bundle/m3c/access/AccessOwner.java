package bundle.m3c.access;

public class AccessOwner {
    public static int publicValue = 101;
    static int packageValue = 23;
    private static int privateValue = -7;

    static int readPrivate() {
        return privateValue;
    }

    static int updatePrivate(int value) {
        privateValue = value;
        return privateValue;
    }
}
