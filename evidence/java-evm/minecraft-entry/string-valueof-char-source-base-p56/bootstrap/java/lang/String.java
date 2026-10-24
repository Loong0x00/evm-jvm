package java.lang;

import java.util.Locale;
import java.util.regex.Pattern;
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
  public native String toLowerCase(Locale locale);
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
  /** Replaces all non-overlapping matches in the supported compiled Pattern profile. */
  public String replaceAll(String regex, String replacement) {
    return Pattern.compile(regex).matcher(this).replaceAll(replacement);
  }
  public int indexOf(int ch) {
    int receiverLength = length();
    if (ch < 0x10000) {
      for (int index = 0; index < receiverLength; index++) {
        if (charAt(index) == ch) return index;
      }
    } else if (ch <= 0x10ffff) {
      int delta = ch - 0x10000;
      char high = (char) ((delta >>> 10) + 0xd800);
      char low = (char) ((delta & 0x3ff) + 0xdc00);
      for (int index = 0; index < receiverLength - 1; index++) {
        if (charAt(index) == high && charAt(index + 1) == low) return index;
      }
    }
    return -1;
  }
}
