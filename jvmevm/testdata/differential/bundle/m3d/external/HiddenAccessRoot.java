package bundle.m3d.external;

import bundle.m3d.hidden.PublicChild;

public class HiddenAccessRoot {
    public static int publicInheritedField(int input) {
        return PublicChild.value + input;
    }

    public static int publicInheritedMethod(int input) {
        return PublicChild.compute(input);
    }

    public static int publicInheritedVoid(int input) {
        PublicChild.store(input);
        return PublicChild.value;
    }
}
