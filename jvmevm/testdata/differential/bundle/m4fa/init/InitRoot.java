package bundle.m4fa.init;

/** Abstract-interface metadata may contain <clinit>, but these operations must not initialize it. */
public class InitRoot {
    private static int call(InitFace receiver, int value) {
        return receiver.read(value);
    }

    public static int allocationDoesNotInitialize(int value) {
        new InitImpl();
        return InitProbe.read() * 100 + value;
    }

    public static int interfaceCallDoesNotInitialize(int value) {
        return call(new InitImpl(), value) + InitProbe.read() * 1000;
    }

    public static int inheritedCallDoesNotInitialize(int value) {
        InitFace receiver = new InitInherited();
        return receiver.read(value) + InitProbe.read() * 1000;
    }

    public static int interfaceArrayDoesNotInitialize(int value) {
        InitFace[] values = new InitFace[2];
        return InitProbe.read() * 100 + values.length + value;
    }

    public static int interfaceMatrixDoesNotInitialize(int value) {
        InitFace[][] values = new InitFace[2][3];
        return InitProbe.read() * 1000 + values.length * 10 + values[0].length + value;
    }

    public static int interfaceCastDoesNotInitialize(int value) {
        Object object = new InitImpl();
        InitFace face = (InitFace) object;
        return face.read(value) + InitProbe.read() * 1000;
    }

    public static int interfaceTestDoesNotInitialize(int value) {
        Object object = new InitImpl();
        return object instanceof InitFace ? value + InitProbe.read() * 1000 : -1;
    }

    public static int diamondDoesNotInitialize(int value) {
        InitLeaf receiver = new InitDiamond();
        return receiver.read(value) + InitProbe.read() * 1000;
    }

    public static int diamondArrayDoesNotInitialize(int value) {
        InitLeaf[][] values = new InitLeaf[1][2];
        return InitProbe.read() * 1000 + values.length * 10 + values[0].length + value;
    }

    public static int unusedMetadataDoesNotInitialize(int value) {
        return InitProbe.read() == 0 ? value : -1;
    }
}

class InitProbe {
    static int counter;
    static int bump() { counter++; return counter; }
    static int read() { return counter; }
}

interface InitFace {
    int TOKEN = InitProbe.bump();
    int read(int value);
}

interface InitLeft extends InitFace {
    int LEFT_TOKEN = InitProbe.bump();
}

interface InitRight extends InitFace {
    int RIGHT_TOKEN = InitProbe.bump();
}

interface InitLeaf extends InitLeft, InitRight {
    int LEAF_TOKEN = InitProbe.bump();
}

class InitImpl implements InitFace {
    public int read(int value) { return value + 1; }
}

class InitBareBase {
    public int read(int value) { return value + 2; }
}

class InitInherited extends InitBareBase implements InitFace {
}

class InitDiamond implements InitLeaf {
    public int read(int value) { return value + 3; }
}
