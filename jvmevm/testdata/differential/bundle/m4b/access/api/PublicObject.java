package bundle.m4b.access.api;

public class PublicObject {
    public int number;
    public Object reference;

    public PublicObject(int number) { this.number = number; }

    public static int read(PublicObject value) { return value.number; }
    public static PublicObject pass(PublicObject value) { return value; }
}
