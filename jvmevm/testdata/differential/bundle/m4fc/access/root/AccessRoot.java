package bundle.m4fc.access.root;

import bundle.m4fc.access.api.ApiBox;
import bundle.m4fc.access.api.PublicApi;

/** Cross-package public interface static methods and inherited public fields. */
public class AccessRoot {
    public static int publicStatic(int value) { return PublicApi.call(value); }
    public static int publicFactory(int value) { return PublicApi.make(value).value; }
    public static int inheritedHiddenOwnerField(int value) { return PublicApi.HIDDEN + value; }
    public static int inheritedFieldViaMethod(int value) { return PublicApi.inheritedField(value); }
    public static int ownPublicField(int value) { return PublicApi.OWN + value; }
    public static int ownFieldViaMethod(int value) { return PublicApi.ownField(value); }
    public static int publicFactoryIdentity(int value) { ApiBox box = PublicApi.make(value); return box.value; }
}
