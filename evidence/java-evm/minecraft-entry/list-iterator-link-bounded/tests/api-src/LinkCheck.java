import java.util.Iterator;
import java.util.ListIterator;
import java.util.NoSuchElementException;

interface SideMarker {}
interface CursorContract extends ListIterator<Object>, SideMarker {}
abstract class CursorBase implements CursorContract {}
final class Cursor extends CursorBase {
    private int cursor;
    public boolean hasNext() { return cursor == 0; }
    public Object next() { if (cursor != 0) throw new NoSuchElementException(); cursor++; return "item"; }
    public boolean hasPrevious() { return cursor != 0; }
    public Object previous() { cursor--; return "item"; }
    public int nextIndex() { return cursor; }
    public int previousIndex() { return cursor - 1; }
    public void remove() {}
    public void set(Object value) {}
    public void add(Object value) {}
}

public final class LinkCheck {
    private static void require(boolean ok) { if (!ok) throw new AssertionError(); }
    public static void main(String[] args) {
        Cursor cursor = new Cursor();
        Object object = cursor;
        require(object instanceof Iterator);
        require(object instanceof ListIterator);
        require(object instanceof CursorContract);
        require(object instanceof SideMarker);
        CursorContract typed = (CursorContract) object;
        Iterator<Object> inherited = typed;
        require(inherited.hasNext());
        require("item".equals(inherited.next()));
        require(!inherited.hasNext());
        try { inherited.next(); throw new AssertionError(); }
        catch (NoSuchElementException expected) {}
        ListIterator<?>[] values = new ListIterator<?>[1];
        values[0] = typed;
        Object copy = values.clone();
        require(copy instanceof ListIterator[]);
        require(((ListIterator<?>[]) copy)[0] == typed);
        try { ((Iterator<?>) null).hasNext(); throw new AssertionError(); }
        catch (NullPointerException expected) {}
        try { ListIterator<?> bad = (ListIterator<?>) new Object(); throw new AssertionError(); }
        catch (ClassCastException expected) {}
    }
}
