package java.lang;
/** Minimal owned Object bootstrap; equals is ordinary default identity. */
public class Object {
    public Object() {}
    public boolean equals(Object other) { return this == other; }
}
