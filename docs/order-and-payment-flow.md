# Order and payment flow

Checkout snapshots the selected address, product names, SKUs, variant attributes, prices, and line totals into an order. A simulated payment is created for the server-calculated order total. Signed callbacks are idempotent by event ID and decrement stock with a conditional update.
