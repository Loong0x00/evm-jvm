import java.util.HashMap;
import java.util.Set;

/** Generated-only negative guest: equals must raw-refuse, not use identity semantics. */
public final class EntrySetUnsupportedProbe {
    public static void main(String[] ignored) {
        HashMap<Object, Object> map = new HashMap<Object, Object>();
        Set<?> view = map.entrySet();
        view.equals(view);
    }
}
