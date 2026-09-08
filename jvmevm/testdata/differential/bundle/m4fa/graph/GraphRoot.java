package bundle.m4fa.graph;

/** Interface inheritance, diamonds, multiple implementations, and stable b9 dispatch sites. */
public class GraphRoot {
    private static int call(GraphValue receiver, int value) {
        return receiver.apply(value);
    }

    private static int parentCall(GraphParent receiver, int value) {
        return receiver.apply(value);
    }

    private static int leftCall(GraphLeft receiver, int value) {
        return receiver.apply(value);
    }

    private static int rightCall(GraphRight receiver, int value) {
        return receiver.apply(value);
    }

    public static int directImplementation(int value) {
        return call(new GraphDirect(), value);
    }

    public static int childInterfaceImplementation(int value) {
        return parentCall(new GraphChildImpl(), value);
    }

    public static int childView(int value) {
        GraphChild receiver = new GraphChildImpl();
        return receiver.apply(value);
    }

    public static int diamondParentView(int value) {
        return parentCall(new GraphDiamondImpl(), value);
    }

    public static int diamondLeftView(int value) {
        return leftCall(new GraphDiamondImpl(), value);
    }

    public static int diamondRightView(int value) {
        return rightCall(new GraphDiamondImpl(), value);
    }

    public static int diamondOwnView(int value) {
        GraphDiamond receiver = new GraphDiamondImpl();
        return receiver.apply(value);
    }

    public static int inheritedBaseMethod(int value) {
        return call(new GraphInherited(), value);
    }

    public static int inheritedDeepBaseMethod(int value) {
        return call(new GraphInheritedDeep(), value);
    }

    public static int multipleInterfacesLeft(int value) {
        return leftCall(new GraphMultiple(), value);
    }

    public static int multipleInterfacesRight(int value) {
        return rightCall(new GraphMultiple(), value);
    }

    public static int alternatingDirectChild(int value) {
        return call(new GraphDirect(), value) * 100 + call(new GraphChildImpl(), value);
    }

    public static int alternatingChildDirect(int value) {
        return call(new GraphChildImpl(), value) * 100 + call(new GraphDirect(), value);
    }

    public static int alternatingDiamondInherited(int value) {
        return call(new GraphDiamondImpl(), value) * 100 + call(new GraphInherited(), value);
    }

    public static int repeatedPolymorphicSite(int value) {
        GraphValue first = new GraphDirect();
        GraphValue second = new GraphChildImpl();
        return call(first, value) + call(second, value) + call(first, value + 1) + call(second, value + 1);
    }

    public static int interfaceRecursion(int depth) {
        GraphRecursive recursive = new GraphRecursive();
        return recursive.step(depth);
    }

    public static int interfaceMutualRecursion(int depth) {
        GraphBounce first = new GraphBounceA();
        GraphBounce second = new GraphBounceB();
        return first.bounce(second, depth);
    }
}

interface GraphValue {
    int apply(int value);
}

interface GraphParent extends GraphValue {
}

interface GraphChild extends GraphParent {
}

interface GraphLeft extends GraphParent {
    int apply(int value);
}

interface GraphRight extends GraphParent {
    int apply(int value);
}

interface GraphDiamond extends GraphLeft, GraphRight {
}

class GraphDirect implements GraphValue {
    public int apply(int value) { return value + 1; }
}

class GraphChildImpl implements GraphChild {
    public int apply(int value) { return value + 2; }
}

class GraphDiamondImpl implements GraphDiamond {
    public int apply(int value) { return value + 3; }
}

class GraphBareBase {
    public int apply(int value) { return value + 4; }
}

class GraphInherited extends GraphBareBase implements GraphValue {
}

class GraphInheritedDeep extends GraphInherited {
}

class GraphMultiple implements GraphLeft, GraphRight {
    public int apply(int value) { return value + 5; }
}

interface GraphStep {
    int step(int depth);
}

class GraphRecursive implements GraphStep {
    public int step(int depth) {
        GraphStep next = this;
        if (depth == 0) {
            return 1;
        }
        return depth + next.step(depth - 1);
    }
}

interface GraphBounce {
    int bounce(GraphBounce other, int depth);
}

class GraphBounceA implements GraphBounce {
    public int bounce(GraphBounce other, int depth) {
        if (depth == 0) {
            return 1;
        }
        return depth + other.bounce(this, depth - 1);
    }
}

class GraphBounceB implements GraphBounce {
    public int bounce(GraphBounce other, int depth) {
        if (depth == 0) {
            return 2;
        }
        return depth * 2 + other.bounce(this, depth - 1);
    }
}
