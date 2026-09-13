import java.util.Properties;
/** Parent-generated TEST only: distinguish super lookup from virtual overrides. */
public final class OverrideProbe extends Properties {
    static int gets, puts, done;
    public Object get(Object key) { gets++; return super.get(key); }
    public Object put(Object key, Object value) { puts++; return super.put(key, value); }
    static final class VirtualDefaults extends Properties {
        public String getProperty(String key) { return "dynamic-default"; }
    }
    private static void require(boolean ok) {
        if (!ok) { int[] zero = new int[1]; int ignored = 1 / zero[0]; }
    }
    public static void main(String[] args) {
        OverrideProbe p = new OverrideProbe();
        p.setProperty("one", "value");
        require(puts == 1); // setProperty must keep its Java virtual put call
        require(p.getProperty("one").equals("value"));
        require(gets == 0); // getProperty must bypass overridden get
        require(p.get("one").equals("value") && gets == 1);
        Properties child = new Properties(new VirtualDefaults());
        require(child.getProperty("missing").equals("dynamic-default"));
        done = 412;
    }
}
