import java.util.Collection;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;

public final class SingletonListProbe {
    private static void require(boolean value) {
        if (!value) { int fail = 1 / 0; }
    }

    public static void main(String[] args) {
        Object token = new Object();
        List<Object> list = Collections.singletonList(token);
        Collection<Object> collection = list;
        Iterable<Object> iterable = list;
        require(list.size() == 1);
        require(!list.isEmpty());
        require(collection.size() == 1 && !collection.isEmpty());

        Iterator<Object> first = iterable.iterator();
        Iterator<Object> second = list.iterator();
        require(first != second);
        require(first.hasNext());
        require(second.hasNext());
        require(first.next() == token);
        require(!first.hasNext());
        require(second.hasNext());
        require(second.next() == token);
        require(!second.hasNext());
        try {
            first.next();
            require(false);
        } catch (java.util.NoSuchElementException expected) { }

        List<Object> another = Collections.singletonList(token);
        require(another != list);
        require(another.iterator() != list.iterator());
        require(another.iterator().next() == token);

        Object[] emptyArray = new Object[0];
        List<Object[]> arrayAsElement = Collections.singletonList(emptyArray);
        require(arrayAsElement.size() == 1);
        require(arrayAsElement.iterator().next() == emptyArray);

        List<Object> nullList = Collections.singletonList(null);
        require(nullList.size() == 1);
        require(!nullList.isEmpty());
        require(nullList.iterator().hasNext());
        require(nullList.iterator().next() == null);
    }
}
