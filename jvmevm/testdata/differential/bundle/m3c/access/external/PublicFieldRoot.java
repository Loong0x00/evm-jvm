package bundle.m3c.access.external;

import bundle.m3c.access.AccessOwner;

public class PublicFieldRoot {
    public static int readAcrossPackage(int addend) {
        return AccessOwner.publicValue + addend;
    }

    public static int writeAcrossPackage(int value) {
        AccessOwner.publicValue = value;
        return AccessOwner.publicValue;
    }
}
