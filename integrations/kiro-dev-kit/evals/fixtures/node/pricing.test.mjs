import test from "node:test";
import assert from "node:assert/strict";
import { discountedCents } from "./pricing.mjs";
test("whole and fractional cent discounts round the discount down", () => {
  assert.equal(discountedCents(100, 20), 80);
  assert.equal(discountedCents(101, 20), 81);
  assert.equal(discountedCents(3, 50), 2);
});
test("zero and full discounts", () => {
  assert.equal(discountedCents(0, 15), 0);
  assert.equal(discountedCents(105, 0), 105);
  assert.equal(discountedCents(105, 100), 0);
});
test("invalid input is rejected", () => {
  for (const args of [[-1, 5], [1.5, 20], [100, -1], [100, 101], [100, 1.5], [Number.MAX_SAFE_INTEGER, 100]]) {
    assert.throws(() => discountedCents(...args), RangeError);
  }
});
