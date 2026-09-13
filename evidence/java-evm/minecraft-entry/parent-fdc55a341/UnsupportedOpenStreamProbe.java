import java.net.URL;import java.util.Enumeration;
/** Presence/URL are real; content stream remains deliberately unsupported. */
public final class UnsupportedOpenStreamProbe {
 public static void main(String[] x)throws Exception{ClassLoader l=UnsupportedOpenStreamProbe.class.getClassLoader();Enumeration<URL> e=l.getResources("probe/resource.txt");e.nextElement().openStream();}
}
