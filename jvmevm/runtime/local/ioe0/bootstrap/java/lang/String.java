package java.lang;
public final class String implements java.io.Serializable, Comparable<String>, CharSequence {
  private final char[] value;
  private int hash;
  private String() { value = null; }
  public String(char[] source) {
    char[] copy = new char[source.length];
    for (int i = 0; i < source.length; i++) copy[i] = source[i];
    value = copy;
  }
  public String(String source) { value = source.value; hash = source.hash; }
  public native int length();
  public native boolean isEmpty();
  public native char charAt(int index);
  public native boolean equals(Object other);
  public native int hashCode();
  public native String toString();
  public native int compareTo(String other);
  public native String intern();
  public native CharSequence subSequence(int start, int end);
}
