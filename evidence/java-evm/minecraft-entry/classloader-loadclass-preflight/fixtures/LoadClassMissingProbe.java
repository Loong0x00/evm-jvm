public final class LoadClassMissingProbe {
 static class Nested {}
 public static void main(String[] x) throws Exception { Class<?> c=Nested.class; ClassLoader.getSystemClassLoader().loadClass("missing.Nope"); }
}
