// Synthetic input for deterministic structural partitioning.
class ContextExample {
    private int total = 0;

    void update(boolean enabled, int amount) {
        try {
            if (enabled) {
                total += amount;
                record(total);
            } else {
                record(0);
            }
        } catch (RuntimeException error) {
            record(-1);
        } finally {
            finish();
        }
    }

    void record(int value) {}
    void finish() {}
}
