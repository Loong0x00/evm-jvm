package bundle.m4b.access.child;

import bundle.m4b.access.api.PublicObject;
import bundle.m4b.access.base.ProtectedBase;

/** Valid public and subclass-protected object accesses across packages. */
public class CrossAccessRoot extends ProtectedBase {
    public CrossAccessRoot(int value) { super(value); }

    private int readProtected(int add) { return protectedValue + add; }
    private int callDirectSuper(int add) { return super.directValue(add); }

    public static int publicConstructorField(int value) {
        PublicObject object = new PublicObject(value);
        return object.number;
    }

    public static int publicFieldWrite(int value) {
        PublicObject object = new PublicObject(1);
        object.number = value;
        return object.number;
    }

    public static int publicReferenceField(int yes) {
        PublicObject first = new PublicObject(1);
        PublicObject second = new PublicObject(2);
        first.reference = second;
        return first.reference == second ? yes : -1;
    }

    public static int publicStaticAccessor(int value) {
        PublicObject object = new PublicObject(value);
        return PublicObject.read(object);
    }

    public static int publicStaticTransport(int yes) {
        PublicObject object = new PublicObject(1);
        return PublicObject.pass(object) == object ? yes : -1;
    }

    public static int protectedField(int value) {
        CrossAccessRoot root = new CrossAccessRoot(value);
        return root.readProtected(3);
    }

    public static int protectedDirectSuper(int value) {
        CrossAccessRoot root = new CrossAccessRoot(value);
        return root.callDirectSuper(4);
    }
}
