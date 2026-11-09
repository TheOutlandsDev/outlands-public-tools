public final class Stock {
    public static int available(int stock, int reserved) {
        if (stock < 0 || reserved < 0) {
            throw new IllegalArgumentException("Nonnegative values required");
        }
        return Math.max(0, stock - reserved);
    }
    public static boolean canFulfill(int stock, int reserved, int quantity) {
        if (quantity < 0) throw new IllegalArgumentException("Nonnegative quantity required");
        return available(stock, reserved) >= quantity;
    }
}
