package java.lang;

/** Minimal Java 8 ClassLoader surface owned by the bounded VM. */
public abstract class ClassLoader {
    protected ClassLoader() {
        super();
    }

    public static native ClassLoader getSystemClassLoader();
    private static native boolean resourceExists(String name);
    private static native Class<?> loadClass0(String name);

    public Class<?> loadClass(String name) throws ClassNotFoundException {
        return loadClass0(name);
    }

    public java.util.Enumeration<java.net.URL> getResources(String name)
            throws java.io.IOException {
        return new VMResourceEnumeration(name, resourceExists(name));
    }
}
