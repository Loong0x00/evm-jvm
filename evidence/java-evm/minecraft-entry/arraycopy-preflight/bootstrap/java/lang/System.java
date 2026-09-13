package java.lang;
/**
 * Deliberately minimal owned bootstrap surface.  The one native declaration is
 * dispatched by the bounded EVM interpreter; it is not a host-JVM call.
 */
public final class System {
    private System() {}
    public static native void arraycopy(Object src, int srcPos,
                                        Object dst, int dstPos, int length);
}
