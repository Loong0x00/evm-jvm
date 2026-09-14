import java.io.Serializable;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

public class ReentrantLocksMain {
    private static void require(boolean value) {
        if (!value) throw new AssertionError();
    }

    public static void main(String[] args) {
        ReentrantLock standalone = new ReentrantLock();
        require(standalone instanceof Lock);
        require(standalone instanceof Serializable);
        Lock lock = standalone;
        lock.lock(); lock.lock(); lock.unlock(); lock.unlock();

        ReentrantReadWriteLock pair = new ReentrantReadWriteLock();
        require(pair instanceof ReadWriteLock);
        require(pair instanceof Serializable);
        ReadWriteLock rw = pair;
        Lock read = rw.readLock();
        Lock write = rw.writeLock();
        require(read == rw.readLock());
        require(write == rw.writeLock());
        require(read != write);
        write.lock(); write.lock(); read.lock(); read.lock();
        read.unlock(); write.unlock(); read.unlock(); write.unlock();
    }
}
