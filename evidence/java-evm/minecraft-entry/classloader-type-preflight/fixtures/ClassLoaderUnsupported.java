/** getSystemClassLoader is deliberately outside this narrow type-only profile. */
public final class ClassLoaderUnsupported {
    public static void main(String[] ignored) {
        ClassLoader.getSystemClassLoader();
    }
}
