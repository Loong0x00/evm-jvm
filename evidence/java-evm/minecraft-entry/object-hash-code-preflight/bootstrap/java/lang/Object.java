package java.lang;

/** Java 8 bounded bootstrap Object: constructor, identity hash, equals, and getClass. */
public class Object {
    public Object() {}
    public boolean equals(Object other) { return this == other; }
    public int hashCode() { return System.identityHashCode(this); }
    public final native Class<?> getClass();
}
