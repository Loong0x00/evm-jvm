package java.util;

/** Minimal genuine Java 8 exception image used by HashMap entry iterators. */
public class ConcurrentModificationException extends RuntimeException {
    private static final long serialVersionUID = -3666751008965953603L;

    public ConcurrentModificationException() { super(); }
}
