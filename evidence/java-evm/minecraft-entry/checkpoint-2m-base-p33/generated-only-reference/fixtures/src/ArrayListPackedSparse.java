public final class ArrayListPackedSparse {
    public static void main(String[] args) {
        float[] packed = new float[1024];
        for (int i = 0; i < packed.length; i++) packed[i] = (float) (i + 1);
        float[] sparse = new float[1024];
        sparse[700] = 5.0f;
        if (packed[0] != 1.0f || packed[1023] != 1024.0f) throw new AssertionError("dense packed values");
        if (sparse[700] != 5.0f || sparse[699] != 0.0f) throw new AssertionError("sparse values");
    }
}
