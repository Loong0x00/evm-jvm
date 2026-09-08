package bundle.m4c.protectedchild;

import bundle.m4c.protectedbase.ProtectedBase;

/** Legal cross-package protected invocation through caller/subclass receivers. */
public class ProtectedRoot extends ProtectedBase {
    private static int scoreAtSite(ProtectedRoot receiver, int add) {
        return receiver.score(add);
    }

    private static void storeAtSite(ProtectedRoot receiver, int value) {
        receiver.store(value);
    }

    public static int inheritedProtected(int value) {
        ProtectedRoot receiver = new ProtectedRoot();
        receiver.value = value;
        return scoreAtSite(receiver, 3);
    }

    public static int selectedProtectedOverride(int value) {
        ProtectedRoot receiver = new ProtectedLeaf();
        receiver.value = value;
        return scoreAtSite(receiver, 4);
    }

    public static int protectedVoidInherited(int value) {
        ProtectedRoot receiver = new ProtectedRoot();
        storeAtSite(receiver, value);
        return receiver.value;
    }

    public static int protectedVoidOverride(int value) {
        ProtectedRoot receiver = new ProtectedLeaf();
        storeAtSite(receiver, value);
        return receiver.value;
    }

    public static int alternatingProtected(int value) {
        ProtectedRoot base = new ProtectedRoot();
        ProtectedRoot leaf = new ProtectedLeaf();
        base.value = value;
        leaf.value = value;
        return scoreAtSite(base, 1) * 100 + scoreAtSite(leaf, 1);
    }
}

class ProtectedLeaf extends ProtectedRoot {
    protected int score(int add) {
        return value * 2 + add;
    }

    protected void store(int value) {
        this.value = value + 10;
    }
}
