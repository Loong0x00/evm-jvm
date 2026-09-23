public final class ArrayHostOracle {
  private ArrayHostOracle() {}

  public static void main(String[] args) {
    int sparseOne = SparseFloatMain.oneDistantNonzero();
    int sparseSeveral = SparseFloatMain.severalDistantNonzeros();
    int dense = DenseFloatMain.verify();
    int small = SmallArrayMain.verify();
    int references = ReferenceArrayMain.verify();
    if (sparseOne != 1 || sparseSeveral != 7 || dense != 65536
        || small != 31 || references != 5) {
      throw new AssertionError("fixture mismatch");
    }
    System.out.println("{\"sparseOne\":1,\"sparseSeveral\":7,\"denseFloatLength\":65536,"
        + "\"smallArrays\":31,\"referenceArray\":5}");
  }
}
