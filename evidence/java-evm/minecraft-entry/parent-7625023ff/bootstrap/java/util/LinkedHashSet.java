package java.util;
import java.io.Serializable;
public class LinkedHashSet<E> extends HashSet<E> implements Set<E>, Cloneable, Serializable {
    public LinkedHashSet() { super(); }
    public LinkedHashSet(int capacity) { super(capacity); }
}
