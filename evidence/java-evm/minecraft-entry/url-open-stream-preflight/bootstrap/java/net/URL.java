package java.net;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;

/** Immutable archive-name URL backed only by the initial read-only VFS seed. */
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
    public InputStream openStream() throws IOException {
        return new FileInputStream(new File("/ro/" + resourceName));
    }
}
