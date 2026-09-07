package bundle.m3d.trace;

public class TraceRoot extends TraceChild {
    static int rootState = append(3);

    public static int superclassOrder(int input) {
        return trace * 1000 + childState * 10 + rootState + input;
    }

    public static int traceOnly(int input) {
        return trace + input;
    }
}
