// HOST TEST ONLY, never in the ZIP or execution driver.
public class Oracle {
    public static void main(String[] args) {
        try { System.out.println("R:" + AliasRoot.run(Integer.parseInt(args[0]))); }
        catch (Throwable t) { System.out.println("X:" + t.getClass().getName()); }
    }
}
