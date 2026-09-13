package java.net;

import java.io.IOException;
import java.io.InputStream;

/** Immutable archive-name URL. No protocol, content or network implementation. */
public final class URL {
    private final String resourceName;
    public URL(String resourceName) { this.resourceName = resourceName; }
    public boolean equals(Object other) {
        if (this == other) return true;
        if (!(other instanceof URL)) return false;
        return resourceName.equals(((URL) other).resourceName);
    }
    public int hashCode() { return resourceName.hashCode(); }
    public String toString() { return resourceName; }
    // Deliberately absent: openStream is unsupported at this bounded presence stage.
}
