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
  public native String substring(int beginIndex);
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
  public boolean startsWith(String prefix) {
    int prefixLength = prefix.length();
    if (prefixLength > length()) return false;
    for (int index = 0; index < prefixLength; index++) {
      if (charAt(index) != prefix.charAt(index)) return false;
    }
    return true;
  }
  // Deliberately bounded to UTF-16 unit equality and ASCII A-Z/a-z folding.
  // This is not a general Unicode case-folding implementation.
  public boolean equalsIgnoreCase(String other) {
    if (other == null) return false;
    int receiverLength = length();
    if (receiverLength != other.length()) return false;
    for (int index = 0; index < receiverLength; index++) {
      char left = charAt(index);
      char right = other.charAt(index);
      if (left == right) continue;
      if (left >= 'A' && left <= 'Z') left = (char) (left + ('a' - 'A'));
      if (right >= 'A' && right <= 'Z') right = (char) (right + ('a' - 'A'));
      if (left != right) return false;
    }
    return true;
  }
  public native String[] split(String regex);
}
