def available(stock, reserved):
    if stock < 0 or reserved < 0:
        raise ValueError("stock and reservations must be nonnegative")
    return max(0, stock - reserved)
