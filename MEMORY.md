# Decision Log

## 2026-08-01, Customer sign-in is phone number + texted code

**What was decided:** Signing in no longer asks for a username and password.
The customer enters their contact number, `POST /auth/customer/login` texts a
6-digit code to it (only if an account exists — otherwise a 404 points them to
sign-up), and the existing `/verify` endpoint completes the session. The auth
sheet now opens in **sign-in** mode when an unauthenticated customer taps
"Proceed to Checkout", with "New here? Create one" underneath. `/resend` now
also works for verified accounts signing back in.

**Why:** Customers forget usernames and passwords; the phone number is the one
credential they always have, it is already the verified SMS destination for
order updates, and the OTP path (hashing, cooldown, attempt lockout) already
existed for signup verification.

**What was rejected:**
- *Keeping username/password sign-in alongside phone sign-in* — two parallel
  login paths for the same launch-stage product adds surface area with no
  customer benefit; `authenticate_customer()` was removed.
- *A separate "login" OTP purpose* — reusing the `phone_verification` purpose
  keeps `/verify` unchanged and both flows prove the same thing: control of
  the number.

**Note:** Signup still collects a username and password even though the
password is no longer used anywhere at sign-in. Whether to drop those fields
from signup is an open follow-up decision.

## 2026-08-01, Order tracking links also go out over SMS (Moolre)

**What was decided:** Every customer notification that carries a tracking link is
now sent over **both** WhatsApp and SMS, with Moolre as the SMS provider. SMS
bodies are deliberately short (one 160-character segment) and carry only the
order reference, total/status and the tracking URL — the full itemised receipt
stays on WhatsApp. Each channel gets its own `notification_events` row, so the
two retry and dedupe independently and an SMS outage cannot suppress the
WhatsApp receipt.

**Why:** WhatsApp delivery is not guaranteed — a customer may not have WhatsApp
installed, may have a different number on the account, or may simply not see the
message. SMS reaches any Ghanaian handset, so the tracking link always lands.

**What was rejected:**
- *SMS replaces WhatsApp entirely* — loses the rich receipt formatting and the
  WhatsApp support thread the platform already depends on.
- *SMS only as a fallback when WhatsApp fails* — cheaper per order, but a
  WhatsApp "sent" result does not prove the customer saw it, so the link could
  still be missed.

**Note:** This supersedes the earlier `AGENT.md` line that made WhatsApp the sole
receipt/notification/tracking-return channel. WhatsApp remains the support
channel and the richer of the two receipts.

**Status:** Integration built and unit-tested, but `SMS_ENABLED` defaults to
`false`. The exact Moolre request/response shape is still provisional — their
SMS API is documented behind the app.moolre.com dashboard, not in the public
payments docs — and lives in a single function, `_moolre_send_request()` in
`backend/app/services/sms.py`. Confirm it before enabling.
