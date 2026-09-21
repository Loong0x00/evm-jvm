package java.util;

public final class Objects {
    private Objects() {}

    public static <T> T requireNonNull(T value, String message) {
        if (value == null) throw new NullPointerException();
        return value;
    }
}
