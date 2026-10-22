/** Valid Java regex syntax outside the guest fixed-token profile must refuse atomically. */
public final class StringReplaceAllUnsupported {
    public static void main(String[] args) {
        "aaa".replaceAll("a+", "x");
    }
}
