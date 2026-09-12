public class Base1 { static int s=4; static {s+=6;} public static int run(int x){return Base2.run(x+s)+1;} }
