package bundle.m4d.crosscomponent.root;

import bundle.m4d.crosscomponent.api.PublicComponent;

/** Cross-package component resolution, defaults, and element access. */
public class CrossComponentRoot {
    public static int crossPackageZero(int value) {
        PublicComponent[] values = new PublicComponent[0];
        return values.length == 0 ? value : -1;
    }

    public static int crossPackageDefaults(int value) {
        PublicComponent[] values = new PublicComponent[2];
        return values[0] == null && values[1] == null ? value : -1;
    }

    public static int crossPackageStoreLoad(int value) {
        PublicComponent[] values = new PublicComponent[1];
        values[0] = new PublicComponent(value);
        return values[0].value;
    }
}
