public final class ArrayCloneElementQuotaOOM {
    private static void fail() {
        throw new IllegalArgumentException();
    }

    public static void main(String[] args) {
        int[][] arrays = new int[3][];
        arrays[0] = new int[65536];
        arrays[1] = new int[65536];
        arrays[2] = new int[65536];
        try {
            arrays[0].clone();
            fail();
        } catch (OutOfMemoryError expected) {
            // 196611 ordinary elements leave too little room for a full clone.
        }
    }
}
