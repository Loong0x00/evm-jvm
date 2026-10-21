public final class ArrayCloneNullReceiver {
    private static void fail() {
        throw new IllegalArgumentException();
    }

    public static void main(String[] args) {
        int[] value = null;
        try {
            value.clone();
            fail();
        } catch (NullPointerException expected) {
            // The intrinsic must preserve JVM null-receiver behavior.
        }
    }
}
