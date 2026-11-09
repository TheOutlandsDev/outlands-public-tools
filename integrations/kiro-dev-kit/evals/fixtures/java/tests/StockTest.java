public final class StockTest {
    private static void check(boolean condition) {
        if (!condition) throw new AssertionError("Stock acceptance check failed");
    }
    public static void main(String[] args) {
        check(Stock.available(5, 2) == 3);
        check(Stock.available(2, 5) == 0);
        check(Stock.canFulfill(5, 2, 3));
        check(!Stock.canFulfill(5, 2, 4));
        check(Stock.canFulfill(0, 0, 0));
        for (int[] values : new int[][] {{-1,0,1}, {1,-1,1}, {1,0,-1}}) {
            boolean rejected = false;
            try { Stock.canFulfill(values[0], values[1], values[2]); }
            catch (IllegalArgumentException expected) { rejected = true; }
            check(rejected);
        }
        System.out.println("PASS: Java stock acceptance checks");
    }
}
