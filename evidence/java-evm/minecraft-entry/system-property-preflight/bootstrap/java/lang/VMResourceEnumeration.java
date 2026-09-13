package java.lang;

import java.net.URL;
import java.util.Enumeration;
import java.util.NoSuchElementException;

/** Independent zero-or-one entry cursor owned by the VM profile. */
public final class VMResourceEnumeration implements Enumeration<URL> {
    private final String resourceName;
    private final boolean available;
    private boolean consumed;
    public VMResourceEnumeration(String resourceName, boolean available) {
        this.resourceName = resourceName;
        this.available = available;
    }
    public boolean hasMoreElements() { return available && !consumed; }
    public URL nextElement() {
        if (!hasMoreElements()) throw new NoSuchElementException();
        consumed = true;
        return new URL(resourceName);
    }
}
