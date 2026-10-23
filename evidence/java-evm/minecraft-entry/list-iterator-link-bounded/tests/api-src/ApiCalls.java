import java.util.ListIterator;

final class ApiPrevious { public static void main(String[] args) { ListIterator<Object> it = new Cursor(); it.previous(); } }
final class ApiAdd { public static void main(String[] args) { ListIterator<Object> it = new Cursor(); it.add("x"); } }
final class ApiSet { public static void main(String[] args) { ListIterator<Object> it = new Cursor(); it.set("x"); } }
final class ApiRemove { public static void main(String[] args) { ListIterator<Object> it = new Cursor(); it.remove(); } }
