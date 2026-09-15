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
  public int lastIndexOf(String target) {
    int targetLength = target.length();
    int receiverLength = length();
    if (targetLength == 0) return receiverLength;
    if (targetLength > receiverLength) return -1;
    for (int start = receiverLength - targetLength; start >= 0; start--) {
      int index = 0;
      while (index < targetLength && charAt(start + index) == target.charAt(index)) index++;
      if (index == targetLength) return start;
    }
    return -1;
  }
  public native String[] split(String regex);
}
