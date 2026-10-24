package probe;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.NoSuchElementException;

public final class ArrayListIteratorProbe {
    private static void require(boolean value) {
        if (!value) throw new ArithmeticException();
    }

    private static final class MisleadingSize extends ArrayList {
        public int size() { return 7; }
    }

    public static void main(String[] args) {
        ArrayList<Object> defaultList = new ArrayList<Object>();
        ArrayList<Object> zeroCapacity = new ArrayList<Object>(0);
        ArrayList<Object> capacityThree = new ArrayList<Object>(3);

        Iterator<Object> first = defaultList.iterator();
        Iterator<Object> second = defaultList.iterator();
        Iterator<Object> zero = zeroCapacity.iterator();
        Iterator<Object> three = capacityThree.iterator();
        require(first != second);
        require(first != zero && zero != three);
        require(!first.hasNext() && !second.hasNext());
        require(!zero.hasNext() && !three.hasNext());
        try {
            first.next();
            throw new ArithmeticException();
        } catch (NoSuchElementException expected) {
            // Real Java exception from the ordinary helper next() body.
        }
        require(!second.hasNext());

        Iterator<Object>[] typed = new Iterator[] { first, second };
        Iterator<Object>[] copied = typed.clone();
        require(copied != typed && copied[0] == first && copied[1] == second);
        require(!copied[0].hasNext() && !copied[1].hasNext());

        MisleadingSize subclass = new MisleadingSize();
        require(subclass.size() == 7);
        require(!subclass.iterator().hasNext());

        ArrayList<Object> nullList = null;
        try {
            nullList.iterator();
            throw new ArithmeticException();
        } catch (NullPointerException expected) {
            // Normal invokevirtual null-receiver behavior.
        }

        try {
            String wrong = (String) (Object) first;
            throw new ArithmeticException();
        } catch (ClassCastException expected) {
            // The returned private helper is still an ordinary typed object.
        }
    }
}
