public final class LinkedHashSetHostOracle {
    public static void main(String[] args) {
        LinkedHashSetProbe.main(new String[0]);
        if (LinkedHashSetProbe.result != 631) throw new AssertionError(LinkedHashSetProbe.result);
    }
}
