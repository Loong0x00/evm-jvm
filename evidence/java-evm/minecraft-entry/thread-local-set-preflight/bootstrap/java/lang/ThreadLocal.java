package java.lang;
public final class ThreadLocal {
  private Object value;
  public ThreadLocal() {}
  public Object get() { return value; }
  public void set(Object value) { this.value = value; }
}
