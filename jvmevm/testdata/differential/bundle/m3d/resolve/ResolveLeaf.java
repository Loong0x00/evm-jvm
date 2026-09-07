package bundle.m3d.resolve;

public class ResolveLeaf extends ResolveMiddle {
    public static int inheritedAndHiddenFields(int input) {
        return ResolveLeaf.shared * 10000 + ResolveLeaf.value * 100 + input;
    }

    public static int distinctHiddenFields(int input) {
        return ResolveBase.value * 1000 + ResolveLeaf.value * 10 + input;
    }

    public static int inheritedMethod(int input) {
        return ResolveLeaf.overloaded(input);
    }

    public static int hiddenMethod(int input) {
        return ResolveLeaf.selected(input);
    }

    public static int baseQualifiedMethod(int input) {
        return ResolveBase.selected(input);
    }

    public static int overloadDescriptors(int first, int second) {
        return ResolveLeaf.overloaded(first) * 1000
                + ResolveLeaf.overloaded(first, second);
    }

    public static int inheritedInitialized(int input) {
        return ResolveLeaf.initialized * 100 + input;
    }

    public static int writeInherited(int input) {
        ResolveLeaf.shared = input;
        return ResolveBase.shared;
    }

    public static int writeHidden(int input) {
        ResolveLeaf.value = input;
        return ResolveBase.value * 1000 + ResolveMiddle.value;
    }
}
