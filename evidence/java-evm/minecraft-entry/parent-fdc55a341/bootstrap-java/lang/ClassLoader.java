package java.lang;

import java.io.IOException;
import java.util.Enumeration;

/** Fixed archive loader surface; presence comes only from the EVM coordinator. */
public abstract class ClassLoader {
    protected ClassLoader() {}
    public static native ClassLoader getSystemClassLoader();
    private static native boolean resourceExists(String name);
    public Enumeration<java.net.URL> getResources(String name) throws IOException {
        return new VMResourceEnumeration(name, resourceExists(name));
    }
}
