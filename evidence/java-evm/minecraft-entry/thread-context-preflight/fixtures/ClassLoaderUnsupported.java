/** ClassLoader methods remain outside this type-only profile. */
public final class ClassLoaderUnsupported {
    public static void main(String[] ignored) { ClassLoader.getSystemClassLoader(); }
}
