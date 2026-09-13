package java.util;

/** Minimal Java 8 Properties construction/default-chain surface. */
public class Properties extends Hashtable<Object, Object> {
    protected Properties defaults;

    public Properties() {
        this(null);
    }

    public Properties(Properties defaults) {
        super();
        this.defaults = defaults;
    }

    public String getProperty(String key) {
        Object value = get(key);
        if (value instanceof String) {
            return (String) value;
        }
        return defaults == null ? null : defaults.getProperty(key);
    }

    public String getProperty(String key, String fallback) {
        String value = getProperty(key);
        return value == null ? fallback : value;
    }

    public Object setProperty(String key, String value) {
        return put(key, value);
    }
}
