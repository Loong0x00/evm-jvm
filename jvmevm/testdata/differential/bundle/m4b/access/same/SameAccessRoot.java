package bundle.m4b.access.same;

/** Valid package-private and same-package protected field/constructor access. */
public class SameAccessRoot {
    public static int packageConstructor(int value) {
        PackageObject object = new PackageObject(value);
        return object.number;
    }

    public static int packageFieldWrite(int value) {
        PackageObject object = new PackageObject(1);
        object.number = value;
        return object.number;
    }

    public static int packageReference(int yes) {
        PackageObject first = new PackageObject(1);
        PackageObject second = new PackageObject(2);
        first.next = second;
        return first.next == second ? yes : -1;
    }

    public static int samePackageProtected(int value) {
        PackageObject object = new PackageObject(value);
        return object.protectedNumber;
    }
}

class PackageObject {
    int number;
    protected int protectedNumber;
    PackageObject next;

    PackageObject(int value) {
        number = value;
        protectedNumber = value + 1;
    }
}
