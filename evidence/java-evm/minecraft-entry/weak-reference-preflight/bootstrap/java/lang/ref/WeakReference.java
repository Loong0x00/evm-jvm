package java.lang.ref;
public class WeakReference {
  private final Object referent;
  public WeakReference(Object referent) { this.referent = referent; }
  public Object get() { return referent; }
}
