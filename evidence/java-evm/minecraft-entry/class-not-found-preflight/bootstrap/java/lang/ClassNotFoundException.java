package java.lang;

/** Minimal owned Java 8 checked exception for immutable Program lookup misses. */
public class ClassNotFoundException extends ReflectiveOperationException {
    public ClassNotFoundException() { super(); }
}
