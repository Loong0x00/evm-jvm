package bundle.m4fc.basic;

/** Public interface entry points exercise root selection and CP InterfaceMethodref calls. */
public interface PublicStatics {
    static int root(int value) { return value + 100; }
    static int pair(int first, int second) { return first * 100 + second; }
    static int nested(int value) { return BasicStatics.twice(value) + root(1); }
    static int classRoundTrip(int value) { return BasicClass.callsInterface(value); }
    static int defaultRoundTrip(int value) { return new BasicImpl().fromDefault(value); }
}
