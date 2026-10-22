import java.util.regex.*;
public class AnchorOracle {
  public static void main(String[] x) {
    String[] tail={"", "\n", "\r", "\r\n", "\u0085", "\u2028", "\u2029", "x\n"};
    for (String s:tail) {
      Matcher m=Pattern.compile("^a$").matcher("a"+s);
      System.out.println(Integer.toHexString(s.length()==0?0:s.charAt(s.length()-1))+":"+m.matches()+":"+Pattern.compile("$").matcher("a"+s).replaceAll("X"));
    }
  }
}
