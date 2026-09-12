public class Base2 { static int s=5; static {s+=7;} public static int run(int x){return Base3.run(x+s)+2;} }
