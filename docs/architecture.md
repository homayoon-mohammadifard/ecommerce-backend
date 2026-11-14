# Architecture

`accounts` owns users, OTP authentication, JWT integration, and addresses. `store` owns catalog and variants. `cart` owns the current user cart. `orders` owns checkout and immutable order snapshots. `payments` contains a simulated, idempotent provider boundary.

Prices, totals, roles, inventory, and payment state are server-owned. PostgreSQL constraints and transactions enforce invariants that cannot safely be enforced only in serializers.
