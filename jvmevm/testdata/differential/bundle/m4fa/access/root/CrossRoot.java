package bundle.m4fa.access.root;

import bundle.m4fa.access.api.PublicFace;

/** Cross-package public interface edges, calls, inherited implementation, and arrays. */
public class CrossRoot {
    private static int call(PublicFace receiver, int value) {
        return receiver.apply(value);
    }

    public static int directPublicInterface(int value) {
        return call(new CrossDirect(), value);
    }

    public static int inheritedPublicMethod(int value) {
        return call(new CrossInherited(), value);
    }

    public static int alternatingPublicInterface(int value) {
        return call(new CrossDirect(), value) * 100 + call(new CrossInherited(), value);
    }

    public static int publicInterfaceArray(int value) {
        PublicFace[] values = new PublicFace[2];
        values[1] = new CrossDirect();
        return values[1].apply(value);
    }

    public static int publicInterfaceMatrix(int value) {
        PublicFace[][] values = new PublicFace[2][1];
        values[1][0] = new CrossInherited();
        return values[1][0].apply(value);
    }

    public static int publicInterfaceCast(int value) {
        Object object = new CrossInherited();
        return ((PublicFace) object).apply(value);
    }
}

class CrossDirect implements PublicFace {
    public int apply(int value) { return value + 51; }
}

class CrossBase {
    public int apply(int value) { return value + 52; }
}

class CrossInherited extends CrossBase implements PublicFace {
}
