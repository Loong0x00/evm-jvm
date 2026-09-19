package java.lang;

/**
 * Bounded Java 8 guest surface: construction, append(String), and toString.
 * Logical content owns an exact-length char array; capacity remains unexposed.
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
        char[] next = new char[value.length + input.length()];
        for (int index = 0; index < value.length; index++) {
            next[index] = value[index];
        }
        for (int index = 0; index < input.length(); index++) {
            next[value.length + index] = input.charAt(index);
        }
        value = next;
        return this;
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
