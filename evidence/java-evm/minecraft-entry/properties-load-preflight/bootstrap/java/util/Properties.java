package java.util;

import java.io.IOException;
import java.io.InputStream;

/** Bounded ISO-8859-1 Properties.load subset; not the general Java SE parser. */
public class Properties extends Hashtable {
    protected Properties defaults;

    public Properties() {
        this(null);
    }

    public Properties(Properties defaults) {
        super();
        this.defaults = defaults;
    }

    public String getProperty(String key) {
        Object value = super.get(key);
        if (value instanceof String) {
            return (String) value;
        }
        if (defaults != null) return defaults.getProperty(key);
        return null;
    }

    public String getProperty(String key, String fallback) {
        String value = getProperty(key);
        if (value != null) return value;
        return fallback;
    }

    public Object setProperty(String key, String value) {
        return put(key, value);
    }

    /**
     * Read ordinary non-escaped ISO-8859-1 property lines. Backslash syntax,
     * including continuation and Unicode escapes, is intentionally rejected.
     */
    public void load(InputStream input) throws IOException {
        char[] line = new char[4096];
        int length = 0;
        while (true) {
            int next = input.read();
            if (next != -1 && next != '\r' && next != '\n') {
                if (next == '\\' || length == 4096) throw new IOException();
                line[length++] = (char) next;
                continue;
            }
            int at = 0;
            while (at < length && (line[at] == ' ' || line[at] == '\t' || line[at] == '\f')) ++at;
            if (at != length && line[at] != '#' && line[at] != '!') {
                int keyStart = at;
                while (at < length && line[at] != '=' && line[at] != ':' && !(line[at] == ' ' || line[at] == '\t' || line[at] == '\f')) ++at;
                int keyEnd = at;
                if (at < length && (line[at] == ' ' || line[at] == '\t' || line[at] == '\f')) {
                    while (at < length && (line[at] == ' ' || line[at] == '\t' || line[at] == '\f')) ++at;
                }
                if (at < length && (line[at] == '=' || line[at] == ':')) ++at;
                while (at < length && (line[at] == ' ' || line[at] == '\t' || line[at] == '\f')) ++at;
                char[] key = new char[keyEnd - keyStart];
                char[] value = new char[length - at];
                for (int i = 0; i < key.length; ++i) key[i] = line[keyStart + i];
                for (int i = 0; i < value.length; ++i) value[i] = line[at + i];
                super.put(new String(key), new String(value));
            }
            if (next == -1) return;
            length = 0;
        }
    }

}
