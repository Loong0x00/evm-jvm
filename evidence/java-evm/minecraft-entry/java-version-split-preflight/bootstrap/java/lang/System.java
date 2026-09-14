package java.lang;
import java.util.Properties;
public final class System {
  private static java.security.SecurityManager security;
  private static Properties properties;
  private System() {}
  public static native void arraycopy(Object src, int srcPos, Object dest, int destPos, int length);
  public static java.security.SecurityManager getSecurityManager() { return security; }
  public static String getProperty(String key) {
    if (key.length() == 0) throw new IllegalArgumentException();
    return properties.getProperty(key);
  }
  static { properties = new Properties(); properties.setProperty("java.version", "1.8"); }
}
