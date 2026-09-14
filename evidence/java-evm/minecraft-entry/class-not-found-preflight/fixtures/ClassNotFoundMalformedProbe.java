public final class ClassNotFoundMalformedProbe {
    public static void main(String[] args) {
        try { ClassNotFoundMalformedProbe.class.getClassLoader().loadClass("bad/name"); throw new Error(); }
        catch (ClassNotFoundException expected) { }
    }
}
