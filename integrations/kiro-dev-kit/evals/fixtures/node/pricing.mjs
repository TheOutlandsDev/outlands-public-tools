export function discountedCents(cents, percent) {
  if (!Number.isSafeInteger(cents) || cents < 0 ||
      !Number.isInteger(percent) || percent < 0 || percent > 100 ||
      !Number.isSafeInteger(cents * percent)) {
    throw new RangeError("Use nonnegative integer cents and a percentage from 0 to 100");
  }
  return cents - Math.floor(cents * percent / 100);
}
