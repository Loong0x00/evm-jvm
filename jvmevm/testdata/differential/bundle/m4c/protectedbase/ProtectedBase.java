package bundle.m4c.protectedbase;

/** Declares cross-package protected virtual slots. */
public class ProtectedBase {
    protected int value;

    protected int score(int add) {
        return value + add + 1;
    }

    protected void store(int value) {
        this.value = value;
    }
}
