package java.io;
public class File implements Serializable, Comparable<File> {
    private final String path;

    public File(String pathname) {
        int length = pathname.length();
        char[] work = new char[length];
        int used = 0;
        boolean slash = false;
        for (int i = 0; i < length; i++) {
            char value = pathname.charAt(i);
            if (value == '/') {
                if (slash) continue;
                slash = true;
            } else {
                slash = false;
            }
            work[used++] = value;
        }
        if (used > 1 && work[used - 1] == '/') used--;
        char[] exact = new char[used];
        for (int i = 0; i < used; i++) exact[i] = work[i];
        path = new String(exact);
    }

    public int compareTo(File other) { return path.compareTo(other.path); }

    final String path0() { return path; }
    public boolean exists() { return stat0() != 0; }
    public boolean isFile() { return stat0() == 1; }
    public boolean isDirectory() { return stat0() == 2; }
    public boolean mkdir() { return mkdir0(false) == 1; }
    public boolean mkdirs() { return mkdir0(true) == 1; }

    private native int stat0();
    private native int mkdir0(boolean parents);
}
