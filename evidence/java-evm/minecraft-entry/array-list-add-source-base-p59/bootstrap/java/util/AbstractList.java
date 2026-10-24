package java.util;

/**
 * Minimal Java 8 hierarchy node for the bounded ArrayList(int) bootstrap.
 * It deliberately supplies only the real AbstractCollection chain and List
 * type link; no indexed-list or mutation operations are implemented here.
 */
public abstract class AbstractList extends AbstractCollection implements List {
    protected AbstractList() { }

    // Refusal-only profile declarations: do not inherit Object identity semantics
    // for List content equality/hash before those operations are implemented.
    public native int hashCode();
    public native boolean equals(Object other);
}
