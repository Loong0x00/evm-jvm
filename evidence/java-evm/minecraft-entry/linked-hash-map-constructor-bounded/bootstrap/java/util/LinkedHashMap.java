package java.util;

/**
 * Constructor-only Java 8 LinkedHashMap profile for the local Minecraft VM.
 *
 * Construction is genuine: the ordinary HashMap constructor initializes the
 * inherited loadFactor, and this class initializes the JDK 8 accessOrder flag
 * to false. No order-maintenance nodes or mutation behavior are implemented.
 * The explicit native put override is an unbound profile refusal, preventing
 * virtual Map/HashMap calls from reaching HashMap's unordered put implementation.
 * All other unbound inherited map/default/Object APIs remain refusals.
 */
public class LinkedHashMap<K, V> extends HashMap<K, V> {
    private static final long serialVersionUID = 3801124242820219131L;

    /** JDK 8's access-order selection, faithfully false for this constructor. */
    private final boolean accessOrder;

    public LinkedHashMap() {
        super();
        this.accessOrder = false;
    }

    /** Deliberately unbound; no inherited unordered HashMap mutation. */
    @Override public native V put(K key, V value);
}
