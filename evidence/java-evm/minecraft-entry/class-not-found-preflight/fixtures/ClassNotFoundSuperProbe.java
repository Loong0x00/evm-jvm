public final class ClassNotFoundSuperProbe {
    public static void main(String[] args) {
        try { ClassNotFoundSuperProbe.class.getClassLoader().loadClass("missing.optional.Super"); throw new Error(); }
        catch (ReflectiveOperationException expected) { }
    }
}
