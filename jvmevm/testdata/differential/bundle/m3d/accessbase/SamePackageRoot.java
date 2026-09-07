package bundle.m3d.accessbase;

public class SamePackageRoot {
    public static int fieldAccess(int input) {
        return ProtectedBase.protectedValue + input;
    }

    public static int methodAccess(int input) {
        return ProtectedBase.protectedCompute(input);
    }

    public static int voidAccess(int input) {
        ProtectedBase.protectedStore(input);
        return ProtectedBase.protectedValue;
    }
}
