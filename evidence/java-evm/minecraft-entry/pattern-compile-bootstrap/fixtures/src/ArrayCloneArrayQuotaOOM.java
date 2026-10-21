public final class ArrayCloneArrayQuotaOOM {
    private static void fail() {
        throw new IllegalArgumentException();
    }

    public static void main(String[] args) {
        // Include the entry String[] args array: holders plus its zero-length rows use 4095.
        int[][] holders = new int[4094][0];
        try {
            holders[0].clone();
            fail();
        } catch (OutOfMemoryError expected) {
            // The entry args plus 4095 holder arrays fill the unchanged quota.
        }
    }
}
