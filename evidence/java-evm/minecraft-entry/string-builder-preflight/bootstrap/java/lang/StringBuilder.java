package java.lang;

/**
 * Bounded Java 8 guest surface: construction, append(String), and toString.
 * Each append owns a fresh exact-length char array.  toString delegates its
 * copy to the ordinary guest String(char[]) constructor.
 */
public final class StringBuilder {
    private char[] value;

    public StringBuilder() {
        value = new char[0];
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
}
