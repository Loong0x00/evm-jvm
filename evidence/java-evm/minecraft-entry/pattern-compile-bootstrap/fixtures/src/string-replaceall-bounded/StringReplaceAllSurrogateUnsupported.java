/** Java-valid UTF-16 input outside this char-token matcher's BMP-only profile. */
public final class StringReplaceAllSurrogateUnsupported {
    public static void main(String[] args) {
        "\ud83d\ude00".replaceAll("a", "x");
    }
}
