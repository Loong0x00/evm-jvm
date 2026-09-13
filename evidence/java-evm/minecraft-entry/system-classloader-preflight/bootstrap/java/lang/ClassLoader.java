package java.lang;

/** Minimal Java 8 loader type with only the VM-provided canonical getter. */
public abstract class ClassLoader {
    protected ClassLoader() {
        super();
    }

    public static native ClassLoader getSystemClassLoader();
}
