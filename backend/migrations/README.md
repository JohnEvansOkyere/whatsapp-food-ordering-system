# Backend SQL Migrations

Run these files in order inside the Supabase SQL editor.

## Order

1. `0001_initial_schema.sql`
2. `0002_menu_seed.sql`
3. `0003_multitenant_foundation.sql`
4. `0004_order_operations.sql`
5. `0005_menu_availability.sql`
6. `0006_two_branch_tracking.sql`
7. `0007_launch_operations.sql`

## Notes

- All files are written to be idempotent where practical.
- `0001` and `0002` are the baseline setup for a fresh database.
- `0003` through `0007` are additive migrations that prepare the schema for multitenancy, normalized order items, order audit events, branch availability, private customer tracking, branch menu overrides, and duplicate-order protection.
- The current application still writes to the legacy `orders.items` JSON column. `0004` keeps that column for compatibility while adding normalized tables.
- The launch branch configuration is:
  - tenant slug: `default-tenant`
  - default branch code: `ASHESI`
  - second branch code: `ABELEMKPE`
- The exact public branch phones, coordinates, hours, fees, and service areas
  remain configurable and must be confirmed before launch.
- Public tracking links expire after 90 days by default. Change this documented
  retention period only alongside the customer privacy and support policy.
