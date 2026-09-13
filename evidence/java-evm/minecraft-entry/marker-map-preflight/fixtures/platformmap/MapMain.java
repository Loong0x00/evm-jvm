import java.util.Map;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.ConcurrentHashMap;

/** Generated Java-8 oracle input for the minimal owned map substrate. */
public final class MapMain {
  static Object retained;
  static int state;
  static final class Key {
    final int id;
    Key(int id) { this.id = id; }
    public boolean equals(Object other) {
      return other instanceof Key && ((Key) other).id == id;
    }
    public int hashCode() { return id; }
  }
  private static void require(boolean b) { if (!b) throw new RuntimeException(); }
  public static void main(String[] args) {
    ConcurrentMap<Object,Object> concurrent = new ConcurrentHashMap<Object,Object>();
    Map<Object,Object> map = concurrent;
    require(map.isEmpty());
    try { map.get(null); throw new RuntimeException(); } catch (NullPointerException expected) {}
    Object nonnull = new Key(1);
    try { concurrent.putIfAbsent(null, nonnull); throw new RuntimeException(); } catch (NullPointerException expected) {}
    try { concurrent.putIfAbsent(nonnull, null); throw new RuntimeException(); } catch (NullPointerException expected) {}
    Key first = new Key(7), equal = new Key(7), value = new Key(8), replacement = new Key(9);
    require(map.get(first) == null);
    require(concurrent.putIfAbsent(first, value) == null);
    require(map.get(equal) == value && map.containsKey(equal));
    require(concurrent.putIfAbsent(equal, replacement) == value);
    require(map.get(first) == value && map.size() == 1);
    String left = new String(new char[] {'m','a','p'});
    String right = new String(new char[] {'m','a','p'});
    require(concurrent.putIfAbsent(left, replacement) == null);
    require(map.get(right) == replacement);
    for (int i = 0; i < 3; ++i) require(concurrent.putIfAbsent(new Key(100 + i), new Key(200 + i)) == null);
    require(map.size() == 5);
    retained = value;
    concurrent.clear();
    require(map.isEmpty() && map.size() == 0 && map.get(first) == null && retained == value);
    state = 317;
  }
}
