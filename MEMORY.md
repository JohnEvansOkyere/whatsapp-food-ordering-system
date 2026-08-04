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

**Status:** Superseded on 2026-08-04 — the provider is now Arkesel, not Moolre.
Everything else in this entry (dual-channel sends, short SMS bodies, independent
`notification_events` rows) still stands.

## 2026-08-04, SMS provider switched from Moolre to Arkesel

**What was decided:** The SMS provider is **Arkesel**, replacing Moolre. The
wire format is Arkesel's V1 REST API — a single `GET` to
`https://sms.arkesel.com/sms/api` with `action=send-sms`, the api-key, `to`,
`from` (the approved sender ID) and `sms` as query params, where `code == "ok"`
is the only success value. It lives in one function, `_arkesel_send_request()`
in `backend/app/services/sms.py`. Env keys are `ARKESEL_API_URL`,
`ARKESEL_API_KEY` and `ARKESEL_SENDER_ID`; the `MOOLRE_*` keys are gone.

**Why:** The Moolre integration was never confirmed against a real account — its
request shape was provisional and, as it turns out, wrong (it used the payments
API's `X-API-USER`/`X-API-KEY` headers rather than SMS's `X-API-VASKEY`, and flat
`recipient`/`channel` keys rather than a `messages` array). We have working
Arkesel credentials and a proven Arkesel implementation in the sibling
`leadgeneration` project, so the integration is verifiable rather than assumed.

**What was rejected:**
- *Fixing the Moolre wire format and keeping Moolre as the only provider* —
  Arkesel is the account we actually hold working credentials for.

**Amended the same day:** both providers are now supported as an ordered
failover chain — see the next entry.

**Note:** The sender ID is `Veloxa` — confirmed working from the Arkesel
dashboard on 2026-08-04 — while `RESTAURANT_NAME` is `HallMark Cafe`, so SMS
arrives from "Veloxa" with a body that names HallMark Cafe. That matches the
platform brand (`veloxa.app`), so it is deliberate, not a mismatch to fix.

**Status:** Built and unit-tested against the documented V1 contract, but
`SMS_ENABLED` is still `false` and no live SMS has been sent. Arkesel bills per
segment, so first real send needs explicit sign-off.

## 2026-08-04, SMS providers are an ordered failover chain

**What was decided:** `send_sms()` walks `SMS_PROVIDERS` (default
`arkesel,moolre`) and tries each provider until one accepts the message. A
provider whose credentials are blank is **skipped**, not counted as a failure,
so a one-provider deployment needs no extra configuration and adding the second
is purely a matter of filling in `MOOLRE_VAS_KEY`. Both adapters —
`_arkesel_send_request()` and `_moolre_send_request()` — live in
`backend/app/services/sms.py` behind that one chain.

**Why:** Phone sign-in verification codes go through the same `send_sms()` as
order notifications (`issue_otp()` in `customer_auth_service.py`). A tracking
link that fails to send is an annoyance the customer can work around; a
verification code that fails to send locks them out of their account with no
second channel. One provider being down or out of balance should not be able to
take sign-in with it.

**What was rejected:**
- *A single `SMS_PROVIDER` setting* — makes switching providers a deploy rather
  than a fallback, which is exactly the failure mode that matters for OTPs.
- *Failing over only for verification codes* — the split adds a code path that
  is exercised rarely and would rot; order notifications benefit too, and the
  cost of a retry against a second provider is one extra segment on an outage.
- *Retrying the same provider before moving on* — Arkesel and Moolre both
  return terminal result codes (bad sender ID, no balance), so a retry mostly
  spends latency on a call that will fail identically.

**Note:** Duplicate-send risk is real but bounded — if a provider accepts a
message and then reports a failure, the customer gets two SMS. Moolre sends
carry a unique `ref` for idempotency; Arkesel V1 has no equivalent.

**Status:** Unit-tested (failover, transport-error failover, skip-unconfigured,
all-providers-fail).

## 2026-08-04, Moolre is the live SMS provider; Arkesel is the dormant fallback

**What was decided:** `SMS_PROVIDERS=moolre,arkesel`. Moolre carries the sends;
Arkesel stays configured but second because its API rejects every key we have.

**Why:** Verified directly against both APIs, no SMS spent:
- Moolre `/open/sms/status` → balance `16`, sender ID `Venariq` **Approved**
  (id 4355). The VAS key is a JWT carrying a `vasid` claim.
- Arkesel → `102 Authentication Failed` on V1 and `401 Invalid key` on V2, for
  **two** separately generated keys. Sending the key as a Bearer token returns
  "Missing key" while the `api-key` header returns "Invalid key", which proves
  the scheme and endpoint are right and the account simply does not recognise
  the credential. Dashboard sends work, so this is API access at the account
  level, not the code. Unresolved with Arkesel.

**Note:** On Moolre only `Venariq` is approved — `Veloxa` and `HallMark` both
return "Not Found". So SMS now arrives from **Venariq** with a body naming
HallMark Cafe. `Veloxa` remains the approved sender on Arkesel. Register
`Veloxa` with Moolre if the branding matters before launch.

**Amended the same day:** Arkesel was dropped from the chain entirely —
`SMS_PROVIDERS=moolre`. Moolre is the paid, working account, and leaving a
provider in the chain that rejects every key only spent a failing round-trip
per send and wrote a log line implying a fallback that did not exist. The
Arkesel adapter, tests and env keys all stay in place; re-enabling it is a
matter of adding `arkesel` back to `SMS_PROVIDERS`.

**Status:** Credentials verified live. `SMS_ENABLED=true`. No SMS has actually
been delivered yet — the first real send is still pending.

## 2026-08-04, The order receipt SMS is warm, and capped at one segment

**What was decided:** The order-confirmation SMS greets the customer by first
name and thanks them before giving the tracking link:

> Hi Kofi! Thank you, HallMark Cafe is happy to see you. Order ORD-7F3A21 is
> in, GHS 132.00. Track: https://veloxa.app/track/…

**One segment is a hard budget.** A tracking URL is ~57 characters of the 160
available, so the copy has ~100 to work with. When a long first name would tip
the message into a second segment, `build_receipt_sms()` drops **the name**,
never the thanks or the link — same message, one billed unit instead of two.

**Why:** The receipt was previously a flat "Order X received." Warmth is worth
having on the one message every customer is guaranteed to read. But segments
are money on a small prepaid balance, and a second segment doubles the cost of
every order for a few characters of surname.

**What was rejected:**
- *Letting the message run to two segments* — doubles per-order SMS cost.
- *Truncating long names* ("Nanaadwoa…") — reads worse than no name at all.
- *Keeping the branch name in the SMS* — it was in the old copy but the
  tracking page shows it, and it cost characters the greeting needed.

**Note:** `_first_name()` uses the first whitespace-separated token, so
surnames never reach the message.

**Encoding matters as much as length.** `count_segments()` is GSM-7 *and*
UCS-2 aware: one character outside GSM 03.38 — the `Ɛ`/`Ɔ` of Twi orthography,
a curly quote, an em dash — drops the whole message to 70-character segments,
turning a one-unit send into three. Since the name is customer-supplied, that
is a live risk, and the same fallback handles it: a name that forces UCS-2 is
dropped exactly like a name that is too long. Accented characters inside
GSM-7 (`é`, `à`, `ö`) are kept, because they cost nothing. **Never put an em
dash or curly quote in an SMS body** — they are not in GSM-7.

## 2026-08-04, Checkout collects one map-backed address, and nothing the account already knows

**What was decided:** The checkout form dropped from four inputs to two. The
name field is gone — `customer_name` now comes from the verified account
(`session.customer.name || session.customer.username`), the same place the
phone already came from. The separate "Landmark / Delivery Note" field is gone
too, folded into a single address control (`AddressField`) that does three
things: Google Places autocomplete biased to the branch and restricted to
Ghana, a "Use my location" button that reverse-geocodes the GPS fix, and a
small confirmation map with a fixed centre pin the customer drags to correct
the drop point. What survives is address + payment method.

Provider is **Google Places (New) + Maps JavaScript + Geocoding**, keyed by
`NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`. Coordinates land on the order as
`delivery_latitude` / `delivery_longitude` / `delivery_place_id` (migration
`0009_delivery_location.sql`), and the admin order drawer links a pinned
address straight into Google Maps.

**Why:** The form was long enough to read as a barrier on a phone, and every
field on it was either already known or hard to answer. "Landmark" in
particular asks the customer to do the rider's navigation for them. A pin is
strictly better information than a landmark sentence, and it is free to give.

**What was rejected:**
- *Requiring a Places match before checkout* — Ghanaian addresses like
  "Christina village" often have no match, and blocking those customers costs
  far more than a missing pin. A typed address is always accepted; it is
  labelled "Not on the map — the rider will call you" for staff, and it stores
  null coordinates.
- *OpenStreetMap Nominatim* — free and keyless, but thin coverage off main
  roads in Ghana and a rate-limit policy needing a proxy and cache.
- *GPS-only, no search* — cannot set a destination you are not standing at.
- *Keeping a collapsed optional delivery note* — the request was explicitly one
  field, and the pin replaces what the note was for.

**Hard requirement:** address search failing must never block an order. Every
Google call in `lib/googleMaps.ts` is wrapped so a missing key, a blocked
script, or a failed lookup degrades to a plain typed address field.

## 2026-08-04, The order SMS sends automatically — checkout no longer asks for consent

**What was decided:** The "Send my receipt and order-status updates to this
WhatsApp number" checkbox is gone, and with it the 400 the API returned when
`whatsapp_consent` was false (`public.py`). Placing the order *is* the consent.
`CreateOrderSchema.whatsapp_consent` now defaults to `True`, the web checkout
always sends `true`, and the receipt plus tracking link go to the verified
number automatically. In the checkbox's place is a plain statement of fact:
"Your receipt and tracking link are texted to 054 495 4643."

**Why:** The box was required but styled like a preference, sitting next to a
genuinely optional one, so customers hit a red error on their first order. The
tick also bought nothing: these are transactional messages about the
customer's own order, going to a number they already verified by OTP at
signup. Asking permission to do the thing they just asked for is friction, not
compliance.

**Scope:** operational messages only — receipt, tracking link, status updates.
Nothing about this flag authorises marketing, and if promotional sends are ever
added they need their own separate, genuinely optional opt-in.

**What was rejected:**
- *Keeping the box but pre-ticking it and marking it required* — still a
  question, still a way to fail checkout.
- *Dropping the `whatsapp_consent` field entirely* — the column records that
  the customer was told, and the WhatsApp bot path (`groq_service`) still sets
  it; removing it would have been a wider change than the problem needed.

**Naming note:** the field is still called `whatsapp_consent` and the response
field `whatsapp_receipt_sent`, but delivery is SMS. Customer-facing copy now
says "texted"; the internal names were left alone deliberately.

## 2026-08-04, The customer flow is treated as a phone app, not a responsive site

**What was decided:** The whole customer path — branch picker, menu, product
sheet, cart, checkout, sign-in, tracking — is now built against a 390×844
phone as the primary target rather than as a desktop layout that also reflows.
The concrete rules that came out of it:

- **One viewport, declared in `_app.tsx`,** with `viewport-fit=cover` so
  `env(safe-area-inset-*)` is non-zero. `maximum-scale=1` is gone — it blocked
  pinch zoom, which is an accessibility failure and buys nothing.
- **Text inputs never render below 16px on phones.** iOS Safari zooms the page
  when a focused input is smaller and does not zoom back out. Enforced once in
  `globals.css` at `max-width: 639px`; the sizing utilities apply from `sm:` up.
  The one field that must stay oversized (the OTP box) opts out with an inline
  `style`, because the rule deliberately out-specifies the utility classes.
- **Modals render through a portal to `<body>`.** `CustomerAuthSheet` is opened
  from inside `MobileCartSheet`, whose slide `transform` makes it the containing
  block for `position: fixed` descendants — the sign-in dialog was being
  positioned against the cart sheet and clipped by its `overflow-hidden`.
- **Bottom-anchored UI clears the home indicator** via the `pb-safe`/`mb-safe`
  helpers, and the sticky header clears the translucent status bar with
  `pt-safe`.
- **Tap targets are 36–44px** on the controls customers actually hit repeatedly
  (quantity steppers, add buttons, text links), trimmed back at `sm:` where a
  mouse is doing the work.
- **The hero is one video on phones**, `object-cover`, no blurred fill layer.
  Two full-viewport videos — one behind a 40px blur — doubled the download and
  put two filtered layers in the compositor for no visual gain in portrait.
- **Network calls that gate the UI have a 6s cap** (`fetchWithTimeout` in
  `index.tsx`). A hanging request is worse than a failed one: without the cap
  the branch picker sits on its skeleton forever instead of falling back to
  `FALLBACK_BRANCHES`, which it already has in hand.
- **Tracking stops polling** when the tab is hidden or the order reached a
  terminal state, and refreshes on return. Ten-second polling forever is real
  money on a Ghanaian data bundle.

**Why:** Effectively all ordering traffic is phone traffic, so anything that
only works on a desktop viewport is broken for the actual customer. Several of
these were not "polish" but hard failures — a sign-in sheet clipped inside the
cart, a page permanently zoomed after tapping a field, a checkout button under
the home indicator.

**What was rejected:**
- *Fixing the 16px input floor field-by-field with `text-base sm:text-sm`* —
  correct where applied, but silently reintroduced by the next input anyone
  adds. One rule that cannot be forgotten beats six that can.
- *Switching `apple-mobile-web-app-status-bar-style` to `black`* — avoids the
  overlap without any safe-area work, but gives up the edge-to-edge hero that
  the translucent bar exists for. Handled the insets instead.
- *Dropping the hero video on phones entirely* — the cheapest possible fix, but
  the hero is the brand moment; halving the layers keeps it at half the cost.
- *`AbortSignal.timeout()`* — cleaner, but the tracking link opens inside
  WhatsApp's in-app browser, so the timeout uses `AbortController` for reach.

**Note:** PNG icons (192/512/apple-touch) were generated because iOS ignores an
SVG `apple-touch-icon` and substitutes a screenshot of the page, and Chrome's
install prompt wants a raster icon. The manifest `background_color` was `#fffaf4`
against a `#111111` app, which flashed white on launch.

**Not touched:** `pages/dashboard.tsx` and `pages/admin/*` are staff surfaces on
kitchen tablets and were left alone — the phone-first pass covers the customer
flow only.

## 2026-08-04, The staff dashboard is Kanban-first and hides secondary controls

**What was decided:** `/dashboard` opens on one focused order board with five
live lanes: New, Accepted, Preparing, Ready, and Delivery. Exceptions and closed
orders live in separate tabs. Selecting a card opens its details and approved
status actions in a side drawer; restaurant ordering and sold-out controls live
in a separate Menu & settings drawer.

**Why:** Keeping metrics, menu availability, assistant activity, seven status
lanes, and a permanent order-detail panel visible at once made the screen hard
to scan during service. The board is the staff member's primary job, so it gets
the full workspace and everything secondary appears only when requested.

**What was rejected:**
- *Free drag-and-drop between lanes* — backend-approved transitions, ETA input,
  and exception reasons must remain enforced rather than allowing staff to skip
  audited operational steps.
- *Showing every status in one board* — delayed, cancellation, and historic
  states would recreate the overcrowding the redesign is intended to remove.

## 2026-08-04, Completed orders use a paginated table instead of Kanban lanes

**What was decided:** The Completed tab combines delivered, cancelled, and
rejected orders in one table with an explicit Status column. It is searchable,
sorted newest first, and paginated at 15 orders per page. Live and attention
work remain on Kanban boards.

**Why:** Historic orders accumulate continuously and do not need to be moved
between stages. Separate closed-state lanes waste horizontal space and make a
large archive harder to scan, while a table supports quick comparison across
customer, status, payment, channel, total, and date.

**What was rejected:**
- *Keeping three completed Kanban lanes* — it becomes unwieldy as order history
  grows and hides useful comparison fields inside cards.
- *Changing the live workflow to a table too* — active kitchen orders still
  benefit from the visual stage-by-stage Kanban workflow.

## 2026-08-04, Menu and restaurant settings have a dedicated page

**What was decided:** Menu availability and branch ordering controls live at
`/dashboard/settings`, linked from the persistent dashboard navigation. The
order board no longer loads or displays these controls in a drawer.

**Why:** Menu maintenance is a separate operational task from tracking live
orders. A full page gives the complete item list, search, availability totals,
clear branch context, and room to grow without covering or crowding the order
board.

**What was rejected:**
- *Keeping the side drawer* — it gives a long menu list too little space and
  hides the order board while open.
- *Putting the controls back above the Kanban* — that would recreate the dense
  dashboard layout the redesign removed.

## 2026-08-04, Operational queues are scoped, paginated, and role-safe

**What was decided:** The admin orders API separates `live`, `attention`, and
`closed` scopes before applying limits. Closed history uses database-backed
search, totals, offsets, and 15-row pages. The dashboard polls compact list rows
and loads full items/events only when an order is opened. Backend detail
responses expose only the transitions authorized for the signed-in staff role.

Delivery orders must move from Ready to Out for delivery before Delivered;
pickup and dine-in orders may close from Ready. When the current state is
Delayed or Cancel requested, the order may resume only to the exact stage saved
on the exception event. ETA and exception reasons are collected in the order
drawer rather than browser prompts.

**Why:** A newest-50 mixed query could hide active work behind completed volume,
and loading details for every row created up to 51 requests every 15 seconds per
screen. Generic exception recovery and generic UI actions also asked staff to
make decisions the system already knew, sometimes ending in a permission error.

**What was rejected:**
- *Client-only filtering and pagination* — it cannot see orders outside the
  downloaded slice and gives inaccurate archive totals.
- *One detail request per visible order* — card and table views need summary
  fields only; full detail belongs behind an explicit open action.
- *Letting exceptions resume to any later status* — it permits accidental stage
  jumps and makes the audit trail ambiguous.

## 2026-08-04, The branch picker is a video with two buttons, and nothing else

**What was decided:** The branch picker and the in-app store hero now share one
cinematic video background (`HeroVideo`), and the copy over it is cut to a small
brand line plus one heading. The picker is `HALLMARK CAFE` / `Branches` and a
two-up grid of branch tiles — name and arrow, nothing more. Full-width rows
were tried first and read as banners rather than choices, with a lot of dead
horizontal space; side-by-side tiles fit both branches in one glance. The store hero is
`HALLMARK CAFE` / the branch name.

Gone from the picker: the "Freshly made in Ghana" badge, the three-line
"Hot food. Right branch. No guessing." headline, the WhatsApp explainer
paragraph, and the per-branch address, hours and ETA lines. Gone from the hero:
"Where Ghana eats." The scrim dropped from near-opaque
(`rgba(13,5,2,0.76→0.98)`) to `from-black/60 via-black/25 to-black/85`, weighted
at the bottom where the buttons need contrast and light through the middle where
the footage is.

**Why:** The picker was a wall of text over a static image dark enough to be
invisible — the video the product already ships never actually got seen. The
branch details it listed are all knowable after choosing, and the one fact that
changes the decision (open vs closed) survives as a `Closed` label on a disabled
button.

**What was rejected:**
- *Keeping the Ken Burns image slideshow* — it was the reason the picker looked
  nothing like the rest of the app, and it competed with the video for the same
  job. `BACKGROUND_SLIDES`, `.branch-background-slide`, `branchKenBurns`,
  `.branch-picker-grain` and `.branch-status-pulse` were all removed with it.
- *Duplicating the video markup into the picker* — the mobile treatment (single
  cover-cropped layer, no blur fill, `preload=metadata`) is easy to get wrong
  twice, so it lives in `HeroVideo` and both surfaces call it.
- *Dropping the open/closed state to make the buttons uniform* — sending a
  customer into a closed branch's menu is a real failure, not a style choice.

**Note:** `public/images/menu/entrance-{feast,pizza,jollof}.webp` (936K) are now
unreferenced. Left in place — deleting assets needs a call from Evans.

## 2026-08-04, The entrance leads with the room, the branch pages lead with food

**What was decided:** The two hero surfaces now show different things. The
entrance screen keeps the cafe video (`branch-hero.mp4`). Each branch page
leads with a food still instead — Ashesi gets `entrance-jollof.webp`,
Abelemkpe `entrance-feast.webp`, with `entrance-pizza.webp` as the fallback for
any branch added later. `BranchHeroMedia.videoSrc` is now optional and
`HeroVideo` became `HeroMedia`, rendering an `<Image>` whenever there is no
video — the same path `prefers-reduced-motion` already used.

**Why:** A first-time customer was seeing the identical clip twice within
seconds, because both branches and the picker all pointed at
`DEFAULT_HERO_MEDIA`. Splitting them gives each screen something of its own to
say — the room, then the plate — and food directly above the menu is the spot
where appetite actually matters. A still is also a fraction of the clip on a
phone, at the moment the menu is the next thing to load.

**What was rejected:**
- *Dropping the branch hero entirely* — `index.tsx` remembers the branch in
  `localStorage`, so returning customers skip the entrance screen completely.
  The branch hero is the only one they ever see; removing it opens the app on a
  bare list of menu rows.
- *Using "the food video"* — there isn't one. `14534903-hd_1920_1080_25fps.mp4`
  (8.1MB, unused) is just the 1080p source of the same cafe-interior clip that
  `branch-hero.mp4` is the 720p compression of. Frames from both were checked.
  The food assets in this repo are stills only.

**Note:** The heading block carries its own `text-shadow` rather than the scrim
being darkened. A food still is much brighter than the video it replaced, and
bright in unpredictable places, so dimming the whole photo to suit the type
would have undone the reason for the swap.

**Still open:** `StoreHero` is `86svh` on phones. With a still it is cheap to
load but it is still a full screen between the customer and the menu on every
visit. Dropping it to ~36svh was recommended and not taken up — worth revisiting.

**Note:** `entrance-{jollof,feast,pizza}.webp` are in use again, so the earlier
note about them being dead assets no longer applies. The 8.1MB HD source video
remains unreferenced.
