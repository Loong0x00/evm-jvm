package bundle.m4e.crosscomponent.api;

public class PublicComponent {
    public int value;

    public PublicComponent(int value) {
        this.value = value;
    }

    public int read() {
        return value;
    }
}
