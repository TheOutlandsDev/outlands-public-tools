from inventory import available

def can_fulfill(stock, reserved, quantity):
    if quantity < 0:
        raise ValueError("quantity must be nonnegative")
    return available(stock, reserved) >= quantity
