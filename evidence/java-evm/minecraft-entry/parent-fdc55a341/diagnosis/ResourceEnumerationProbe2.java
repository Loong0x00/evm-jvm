import java.net.URL;
import java.util.Enumeration;
import java.util.NoSuchElementException;

/** Generated trusted fixture: observes the EVM ZI0 presence bridge only. */
public final class ResourceEnumerationProbe2 {
    public static int result;
    public static void main(String[] args) throws Exception {
        ClassLoader loader = ResourceEnumerationProbe2.class.getClassLoader(); if (loader != ClassLoader.getSystemClassLoader()) return;
        Enumeration<URL> first = loader.getResources("probe/resource.txt");
        int v = first.hasMoreElements() ? 1 : 0;
        URL one = first.nextElement();
        if (first.hasMoreElements()) v += 2;
        if (one.equals(one)) v += 4;
        if (one.hashCode() == one.toString().hashCode()) v += 8;
        Enumeration<URL> second = loader.getResources("probe/resource.txt");
        URL two = second.nextElement();
        if (one.equals(two)) v += 16;
        if (one.toString().equals("probe/resource.txt")) v += 32;
        Enumeration<URL> missing = loader.getResources("probe/missing.txt");
        if (!missing.hasMoreElements()) v += 64;
        try { missing.nextElement(); } catch (NoSuchElementException expected) { v += 128; }
        result = v;
    }
}
