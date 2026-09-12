public class Oracle {
    public static void main(String[] args) {
        for (String s : args) System.out.println(s + "=" + SharedEntry.run(Integer.parseInt(s)));
    }
}
