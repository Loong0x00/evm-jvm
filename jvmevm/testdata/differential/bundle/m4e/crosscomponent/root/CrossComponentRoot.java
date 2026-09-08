package bundle.m4e.crosscomponent.root;

import bundle.m4e.crosscomponent.api.PublicComponent;

/** Public cross-package ultimate components resolved by multianewarray. */
public class CrossComponentRoot {
    public static int crossPackageDefaults(int value) {
        PublicComponent[][] values = new PublicComponent[2][1];
        return values[0][0] == null && values[1][0] == null ? value : -1;
    }

    public static int crossPackageStore(int value) {
        PublicComponent[][] values = new PublicComponent[1][2];
        values[0][1] = new PublicComponent(value);
        return values[0][1].read();
    }

    public static int crossPackagePartial(int value) {
        PublicComponent[][][] values = new PublicComponent[2][1][];
        return values[0] != values[1] && values[0][0] == null ? value : -1;
    }
}
