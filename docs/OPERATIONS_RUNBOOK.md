# Restaurant Operations Runbook

## Start of Shift

1. Sign in at `/admin/login` with the account assigned to the branch.
2. Confirm the branch name shown at the top of the dashboard.
3. Enable the new-order sound after interacting with the page.
4. Confirm ordering is enabled.
5. Mark unavailable menu items sold out for that branch.
6. Check `/health/ready` before accepting public orders.

## Normal Order Flow

1. Accept the incoming order.
2. Start preparing when the kitchen begins.
3. Mark ready after packing and final checks.
4. Send for delivery when the rider has the order.
5. Mark delivered only after delivery is confirmed.

Each status creates an audited event before the WhatsApp update is attempted.
Do not skip steps.

## Payments

- Cash orders remain pending until staff selects `Mark cash collected`.
- Mobile Money orders must not be marked paid without a provider or transaction
  reference.
- A real Mobile Money webhook is still required before automated payment
  confirmation.

## Exceptions

- Rejections and cancellations require a reason.
- If another staff member changes the same order first, refresh and review the
  latest state before acting.
- If WhatsApp fails, the order remains valid. Give the customer the private
  tracking link from the order record and use the configured support number.
- If the backend is unavailable, pause new ordering and record orders manually
  until `/health/ready` returns healthy.

## End of Shift

1. Confirm no order remains in `new`, `preparing`, `ready`, or
   `out_for_delivery`.
2. Reconcile paid Mobile Money and collected cash orders.
3. Review failed WhatsApp notification events.
4. Pause ordering if the next shift is not ready to receive orders.
5. Sign out of shared kitchen devices.

## Database Backup and Recovery

Before launch, the operator must confirm that the Supabase plan has scheduled
database backups enabled and record the retention period. Before applying a
migration, create a fresh backup or export and record the migration name and
time.

Recovery procedure:

1. Pause public ordering and preserve the current application logs.
2. Confirm the exact failure time and latest known-good backup.
3. Restore into a separate recovery project or database first.
4. Verify branch, order, order-item, event, payment, and notification counts.
5. Test one private tracking link and one authorized staff login.
6. Redirect production only after the recovered data passes verification.
7. Reconcile any manually accepted orders created during the outage.

Run a documented restore drill before launch. A backup that has never been
restored and verified is not considered launch-ready.
