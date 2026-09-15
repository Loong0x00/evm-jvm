package java.lang;

public abstract class Enum<E extends Enum<E>>
        implements Comparable<E>, java.io.Serializable {
    private final String name;
    private final int ordinal;

    protected Enum(String name, int ordinal) {
        this.name = name;
        this.ordinal = ordinal;
    }

    public final String name() { return name; }
    public final int ordinal() { return ordinal; }
    public String toString() { return name; }
    public final int compareTo(E other) { return ordinal - ((Enum) other).ordinal; }
}
