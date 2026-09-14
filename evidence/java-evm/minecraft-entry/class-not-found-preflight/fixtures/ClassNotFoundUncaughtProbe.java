public final class ClassNotFoundUncaughtProbe {
    public static void main(String[] args) throws ClassNotFoundException { ClassNotFoundUncaughtProbe.class.getClassLoader().loadClass("missing.optional.Uncaught"); }
}
