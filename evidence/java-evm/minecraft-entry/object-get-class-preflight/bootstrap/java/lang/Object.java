package java.lang;

/** Java 8 bounded bootstrap Object: only constructor, equals, and getClass. */
public class Object {
    public Object() {}
    public boolean equals(Object other) { return this == other; }
    public final native Class<?> getClass();
}
