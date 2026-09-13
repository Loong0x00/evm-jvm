public final class CountMain implements Runnable {
  static int sentinel;
  public void run() { sentinel = Tail01.touch() + Tail02.touch() + Tail03.touch() + Tail04.touch() + Tail05.touch() + Tail06.touch() + Tail07.touch() + Tail08.touch() + Tail09.touch() + Tail10.touch() + Tail11.touch() + Tail12.touch() + Tail13.touch() + Tail14.touch() + Tail15.touch() + Tail16.touch() + Tail17.touch() + Tail18.touch() + Tail19.touch() + Tail20.touch() + Tail21.touch() + Tail22.touch() + Tail23.touch(); }
  static void require(boolean ok) { if (!ok) throw new RuntimeException(); }
  public static void main(String[] ignored) {
    CountMain self = new CountMain();
    Runnable supplied = self;
    Class a = Tail23.class, b = Tail23.class;
    require(a == b); require(Tail22.seen == 0);
    require(a.getName().equals("Tail23"));
    supplied.run();
    require(Tail23.touch() == 23);
    require(Tail22.seen == 1);
    Tail23[] from = new Tail23[] { new Tail23(), new Tail23() };
    Tail23[] to = new Tail23[2];
    System.arraycopy(from, 0, to, 0, 2);
    require(to[0] == from[0] && to[1] == from[1]);
    System.arraycopy(to, 0, to, 1, 1);
    require(to[1] == from[0]);
    sentinel += to.length;
  }
}
