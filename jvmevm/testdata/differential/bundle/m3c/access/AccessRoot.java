package bundle.m3c.access;

public class AccessRoot {
    public static int readPublic(int addend) {
        return AccessOwner.publicValue + addend;
    }

    public static int readPackage(int addend) {
        return AccessOwner.packageValue + addend;
    }

    public static int readPrivateThroughOwner(int addend) {
        return AccessOwner.readPrivate() + addend;
    }

    public static int writePublic(int value) {
        AccessOwner.publicValue = value;
        return AccessOwner.publicValue;
    }

    public static int writePackage(int value) {
        AccessOwner.packageValue = value;
        return AccessOwner.packageValue;
    }

    public static int writePrivateThroughOwner(int value) {
        return AccessOwner.updatePrivate(value);
    }

    public static int mixedAccess(int value) {
        AccessOwner.publicValue = value;
        AccessOwner.packageValue = value + 1;
        return AccessOwner.publicValue * 100 + AccessOwner.packageValue * 10
                + AccessOwner.readPrivate();
    }
}
