/** Java8 TEST oracle for standard null/empty checks and absent custom key. */
public final class SystemPropertyHostOracle {
 public static void main(String[] x){
  if(System.getProperty("mc.parent.absent")!=null||System.getProperty("mc.parent.absent")!=null)throw new AssertionError();
  try{System.getProperty(null);throw new AssertionError();}catch(NullPointerException ok){}
  try{System.getProperty("");throw new AssertionError();}catch(IllegalArgumentException ok){}
 }
}
