import java.lang.reflect.Array;
public final class Probe { public static void main(String[] args) { Component[] a=(Component[])Array.newInstance(Component.class,1); Object[] view=a; view[0]=new Object(); } }
