# BUG-102: Checkout returns 500 for every order since the last release

Since yesterday's deploy every checkout attempt fails. Example from the error tracker:

```
Traceback (most recent call last):
  File "sample_app/cart.py", line 10, in checkout
    inventory.reserve(sku, qty)
  File "sample_app/inventory.py", line 23, in reserve
    if STOCK[key] < qty:
KeyError: 'ISBN-0042'
```

The book ISBN-0042 is in stock according to the warehouse CSV. Nothing else changed on our side.
