public final class ArrayCloneNegativeProbe {
    public static void main(String[] args) {
        int[] value = new int[1];
        Object copy = value.clone();
        if (copy == null) throw new IllegalArgumentException();
    }
}
