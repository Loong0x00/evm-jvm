public final class LoadClassMalformedProbe {
 static class Nested {}
 public static void main(String[] x) throws Exception { Class<?> c=Nested.class; ClassLoader.getSystemClassLoader().loadClass("bad/name"); }
}
