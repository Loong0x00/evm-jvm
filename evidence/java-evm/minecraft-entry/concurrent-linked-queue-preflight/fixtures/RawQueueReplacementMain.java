public final class RawQueueReplacementMain {
    public static void main(String[] args) {
        java.util.Queue<Object> q = new java.util.concurrent.ConcurrentLinkedQueue<Object>();
        q.poll();
    }
}
