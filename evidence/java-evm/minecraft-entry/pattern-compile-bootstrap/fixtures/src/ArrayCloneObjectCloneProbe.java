public final class ArrayCloneObjectCloneProbe implements Cloneable {
    public Object copy() throws CloneNotSupportedException {
        return super.clone();
    }

    public static void main(String[] args) throws CloneNotSupportedException {
        new ArrayCloneObjectCloneProbe().copy();
    }
}
