import java.io.Serializable;
import java.util.AbstractCollection;
import java.util.AbstractList;
import java.util.ArrayList;
import java.util.List;
import java.util.RandomAccess;

public final class ArrayListMatrix {
    private static void check(ArrayList list) {
        if (list.size() != 0 || !list.isEmpty()) throw new AssertionError("empty state");
        if (!(list instanceof AbstractList)) throw new AssertionError("AbstractList");
        if (!(list instanceof AbstractCollection)) throw new AssertionError("AbstractCollection");
        if (!(list instanceof List)) throw new AssertionError("List");
        if (!(list instanceof RandomAccess)) throw new AssertionError("RandomAccess");
        if (!(list instanceof Cloneable)) throw new AssertionError("Cloneable");
        if (!(list instanceof Serializable)) throw new AssertionError("Serializable");
        if (list.getClass() != ArrayList.class) throw new AssertionError("class mirror");
    }

    public static void main(String[] args) {
        ArrayList zero = new ArrayList(0);
        ArrayList one = new ArrayList(1);
        ArrayList three = new ArrayList(3);
        ArrayList ten = new ArrayList(10);
        ArrayList thousandTwentyFour = new ArrayList(1024);
        check(zero);
        check(one);
        check(three);
        check(ten);
        check(thousandTwentyFour);
        if (zero == one || one.getClass() != three.getClass()) {
            throw new AssertionError("identity/mirror");
        }
        Object listMirror = List.class;
        if (zero.getClass() == listMirror) throw new AssertionError("distinct class mirrors");
    }
}
