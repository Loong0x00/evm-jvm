package java.util;

import java.io.Serializable;

/** Type-link marker only; no EnumMap construction or Map operation is admitted. */
public class EnumMap extends AbstractMap implements Serializable, Cloneable {
    private EnumMap() { super(); }

    public native Object get(Object key);
    public native Object put(Object key, Object value);
    public native int size();
    public native boolean isEmpty();
    public native void clear();
    public native boolean containsKey(Object key);
    public native Set entrySet();
}
