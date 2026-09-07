package bundle.m3d.accesschild;

public class ProtectedRoot extends ProtectedMiddle {
    public static int crossPackageField(int input) {
        return ProtectedRoot.protectedValue + input;
    }

    public static int crossPackageMethod(int input) {
        return ProtectedRoot.protectedCompute(input);
    }

    public static int crossPackageVoid(int input) {
        ProtectedRoot.protectedStore(input);
        return ProtectedRoot.protectedValue;
    }
}
