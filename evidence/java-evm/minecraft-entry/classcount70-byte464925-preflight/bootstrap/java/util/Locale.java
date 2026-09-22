package java.util;

import java.io.Serializable;

public final class Locale implements Cloneable, Serializable {
    public static final Locale ROOT;

    private Locale() {}

    static {
        ROOT = new Locale();
    }
}
