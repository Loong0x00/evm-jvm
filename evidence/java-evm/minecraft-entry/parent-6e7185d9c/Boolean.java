package java.lang;

import java.io.Serializable;

/** Bounded Java 8 Boolean wrapper used only by the local EVM bootstrap. */
public final class Boolean implements Serializable, Comparable<Boolean> {
    private final boolean value;
    public static final Boolean TRUE = new Boolean(true);
    public static final Boolean FALSE = new Boolean(false);

    public Boolean(boolean value) { this.value = value; }
    public static Boolean valueOf(boolean b) { return b ? TRUE : FALSE; }
    public boolean booleanValue() { return value; }
    public boolean equals(Object obj) {
        return obj instanceof Boolean && value == ((Boolean) obj).booleanValue();
    }
    public int hashCode() { return value ? 1231 : 1237; }
    public static String toString(boolean b) { return b ? "true" : "false"; }
    public String toString() { return toString(value); }
    public static int compare(boolean x, boolean y) { return x == y ? 0 : (x ? 1 : -1); }
    public int compareTo(Boolean b) { return compare(value, b.value); }
}
