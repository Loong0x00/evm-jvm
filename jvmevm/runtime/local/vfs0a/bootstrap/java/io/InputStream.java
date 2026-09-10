package java.io;
public abstract class InputStream implements Closeable {
    protected InputStream() {}
    public abstract int read() throws IOException;
    public int read(byte[] value) throws IOException {
        return read(value, 0, value.length);
    }
    public int read(byte[] value, int offset, int length) throws IOException {
        int capacity = value.length;
        if (offset < 0 || length < 0 || offset > capacity - length) throw new IndexOutOfBoundsException();
        if (length == 0) return 0;
        int next = read();
        if (next == -1) return -1;
        value[offset] = (byte)next;
        int done = 1;
        try {
            for (; done < length; done++) {
                next = read();
                if (next == -1) break;
                value[offset + done] = (byte)next;
            }
        } catch (IOException ignored) {}
        return done;
    }
    public void close() throws IOException {}
}
