package java.lang;

/**
 * Bounded Java 8 guest surface: construction, append(String), append of a
 * validated String-backed CharSequence range, reset, and copy-producing toString.
 */
public final class StringBuilder {
    private char[] value;

    public StringBuilder() {
        value = new char[0];
    }

    public StringBuilder(int capacity) {
        if (capacity < 0) {
            value = new char[capacity];
        } else {
            value = new char[0];
        }
    }

    public StringBuilder append(String input) {
        int prefix = value.length;
        int length = input.length();
        char[] next = new char[prefix + length];
        while (prefix != 0) {
            next[--prefix] = value[prefix];
        }
        while (length != 0) {
            next[value.length + --length] = input.charAt(length);
        }
        value = next;
        return this;
    }

    public StringBuilder append(CharSequence input, int start, int end) {
        if (!(input instanceof String) || start < 0 || end < start || end > ((String) input).length()) {
            throw new IllegalArgumentException();
        }
        char[] slice = new char[end - start];
        while (end != start) {
            slice[--end - start] = ((String) input).charAt(end);
        }
        return append(new String(slice));
    }

    /** Appends exactly one UTF-16 code unit through the retained String path. */
    public StringBuilder append(char input) {
        return append(new String(new char[] { input }));
    }

    public StringBuilder append(int value) {
        if (value < 0) {
            append('-');
        } else {
            value = -value;
        }
        return appendNegative(value);
    }

    private StringBuilder appendNegative(int value) {
        if (value <= -10) {
            appendNegative(value / 10);
        }
        return append((char) ('0' - value % 10));
    }

    public String toString() {
        return new String(value);
    }

    public void setLength(int length) {
        if (length != 0) {
            throw new IllegalArgumentException();
        }
        value = new char[0];
    }
}
