package java.lang.reflect;

/** Minimal Java 8 bootstrap surface for the bounded VM Array primitive. */
public final class Array {
    private Array() { }

    public static Object newInstance(Class<?> componentType, int length)
            throws NegativeArraySizeException {
        return newArray(componentType, length);
    }

    private static native Object newArray(Class<?> componentType, int length)
            throws NegativeArraySizeException;
}
