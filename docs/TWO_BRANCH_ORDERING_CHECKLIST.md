# Two-Branch Ordering and WhatsApp Tracking Checklist

## Goal

Launch a production-ready ordering experience for:

1. Ashesi University
2. Abelemkpe

A customer must be able to select a branch, order through the web app, receive
a private tracking URL through WhatsApp, and follow genuine staff-triggered
progress until delivery.

## Checklist Rules

- `[x]` means the capability is confirmed in the repository.
- `[ ]` means work or real-world verification is still required.
- A code-complete item that depends on an unapplied migration, unapproved
  WhatsApp template, missing credential, or untested deployment stays unchecked.
- Update this document in the same change that completes a material item.

## Current Foundation

- [x] Mobile menu with categories and cart exists.
- [x] Public order creation API exists.
- [x] Backend recalculates order prices from menu data.
- [x] Orders receive order numbers and tracking codes.
- [x] Normalized order items and order event migrations exist in the repository.
- [x] Backend validates allowed order status transitions.
- [x] Public order-tracking API returns the current state and event timeline.
- [x] Customer and restaurant WhatsApp order notifications exist.
- [x] Staff dashboard can list orders and change order status.
- [x] Admin API supports sold-out and active menu controls.
- [ ] Confirm all repository migrations have been applied to the production
  Supabase project.
- [ ] Confirm the production frontend, backend, database, and WhatsApp sender are
  connected and operating together.

## 1. Confirm Launch Configuration

These values must be confirmed before production seed data is finalized.

### Business and brand

- [ ] Confirm the public restaurant name.
- [ ] Add the approved logo, brand colors, type styles, and favicon.
- [ ] Confirm the customer-support phone/WhatsApp number.
- [ ] Confirm whether both branches share one WhatsApp Business number.
- [ ] Confirm who receives owner/escalation notifications.
- [ ] Confirm privacy policy, ordering terms, cancellation policy, and refund
  wording.

### Ashesi University

- [ ] Confirm the exact display address.
- [ ] Confirm map coordinates.
- [ ] Confirm branch phone number.
- [ ] Confirm operating days and hours.
- [ ] Confirm delivery coverage or approved destinations.
- [ ] Confirm standard delivery fee rules.
- [ ] Confirm minimum order, if any.
- [ ] Confirm normal preparation and delivery ETA ranges.

### Abelemkpe

- [ ] Confirm the exact display address.
- [ ] Confirm map coordinates.
- [ ] Confirm branch phone number.
- [ ] Confirm operating days and hours.
- [ ] Confirm delivery coverage or approved destinations.
- [ ] Confirm standard delivery fee rules.
- [ ] Confirm minimum order, if any.
- [ ] Confirm normal preparation and delivery ETA ranges.

### Menu and fulfillment decisions

- [ ] Confirm whether both branches use the same menu.
- [ ] Confirm whether prices can differ by branch.
- [ ] Confirm which products need size or portion variants.
- [ ] Confirm allowed extras and modifier prices.
- [ ] Confirm whether availability is managed separately per branch.
- [ ] Confirm whether the first release is delivery-only or also supports
  pickup.
- [ ] Confirm whether delivery uses restaurant riders, third-party riders, or a
  mixture.
- [ ] Select the launch Mobile Money/payment provider and mark the decision as
  provisional until a live transaction succeeds.

## 2. Branch and Menu Data Model

- [x] Add a new additive migration that seeds `ASHESI` and `ABELEMKPE`; do not
  rewrite an already-applied migration.
- [x] Replace the placeholder `Main Branch` behavior without losing existing
  orders.
- [x] Store branch name, code, address, coordinates, phone, hours, timezone,
  active state, and ordering state.
- [x] Add a public branch endpoint that returns only customer-safe data.
- [x] Decide and implement branch menu inheritance:
  - tenant-wide base menu;
  - per-branch price override;
  - per-branch availability/sold-out override.
- [x] Ensure every new order has a non-null, valid branch.
- [x] Reject inactive or unknown branches at the API boundary.
- [x] Validate menu item availability against the selected branch during order
  creation.
- [x] Add database constraints and indexes for branch order queues.
- [ ] Backfill existing orders to the correct branch or an explicitly documented
  legacy branch.
- [x] Add test seed data for both branches.
- [ ] Verify RLS and service-role policies after the new migration is applied.

## 3. Customer Branch Selection

- [x] Make branch selection the first meaningful ordering decision.
- [x] Present two attractive branch cards:
  - Ashesi University
  - Abelemkpe
- [x] Show open/closed state, hours, approximate service area, and estimated
  delivery time on each card.
- [x] Persist the selected branch across refreshes.
- [x] Keep the branch visible in the header, cart, checkout, success screen,
  WhatsApp receipt, and tracking page.
- [x] Provide a clear `Change branch` action.
- [x] Warn customers before clearing or repricing a cart when switching branch.
- [x] Never switch branches automatically after products have been added.
- [x] Support branch-specific QR/deep links such as `?branch=ashesi`.
- [x] Validate a deep-linked branch before loading its menu.

## 4. Modern Menu and Cart

- [x] Load menu data for the selected branch from the backend.
- [x] Add menu search.
- [x] Add clear category navigation.
- [x] Add product detail sheets/pages.
- [x] Support required variants such as size or portion.
- [x] Support optional extras and modifier groups.
- [x] Support special instructions with a safe length limit.
- [x] Show sold-out items without allowing them to be ordered.
- [x] Show popular items and branch-appropriate recommendations.
- [ ] Add `Frequently bought together` or simple combo upsells.
- [x] Persist the cart locally for accidental refresh/reopen recovery.
- [x] Revalidate all cart prices and availability before checkout.
- [x] Display subtotal, delivery fee, and total separately.
- [ ] Display discounts separately after backend promotion rules exist.
- [x] Optimize food images and provide useful fallbacks.
- [x] Add loading skeletons, helpful empty states, and retryable error states.
- [ ] Verify the menu works on slower mobile connections.

## 5. Checkout and Order Creation

- [x] Keep guest checkout; do not require an account for the first order.
- [x] Collect and validate:
  - Ghana phone/WhatsApp number;
  - customer name;
  - delivery address;
  - landmark and delivery instructions;
  - optional map pin/current location;
  - payment method.
- [ ] Show selected branch and branch contact before confirmation.
- [x] Show an honest ETA range before confirmation.
- [ ] Validate branch operating hours on the backend.
- [ ] Validate the delivery destination against the branch service area.
- [x] Calculate delivery fee on the backend.
- [ ] Calculate discounts and final total on the backend.
- [x] Add order idempotency protection to prevent double-tap duplicate orders.
- [x] Record customer consent needed for operational WhatsApp messages.
- [x] Return the canonical private tracking URL with the order response.
- [x] Show the order number, branch, total, ETA, and tracking button on the
  success screen.
- [ ] Handle unavailable items, branch closure, payment failure, and network
  timeout without losing the cart.

## 6. Secure Tracking Link

- [x] Add a high-entropy, opaque public tracking token; do not rely on a short,
  guessable order number.
- [x] Store and uniquely index the tracking token or its secure lookup value.
- [x] Keep internal order UUIDs out of public URLs.
- [x] Use a canonical route such as `/track/{token}`.
- [x] Ensure the page works without customer login.
- [x] Return only customer-safe order information.
- [x] Add rate limiting and abuse monitoring to the public tracking endpoint.
- [x] Decide and document tracking-link retention/expiry behavior.
- [x] Ensure completed historical links do not expose changing customer data.

## 7. Customer Tracking Page

- [x] Build a polished mobile tracking page.
- [x] Display the selected branch and support contact.
- [x] Display order number, placed time, current status, ETA, payment state, and
  customer-safe order summary.
- [x] Display the normal progress pipeline:
  - Order placed
  - Accepted
  - Preparing
  - Ready
  - Out for delivery
  - Delivered
- [x] Show completed steps, current step, upcoming steps, and event timestamps.
- [x] Show delayed, rejected, and cancelled experiences separately.
- [x] Use database events as the source of truth rather than elapsed-time
  animation.
- [ ] Add Supabase Realtime or equivalent live updates.
- [x] Add a polling fallback when realtime connectivity fails.
- [x] Add `Contact branch on WhatsApp` and `Call branch` actions.
- [x] Add a safe `Need help?` action that includes the order reference.
- [x] Add `Order again` after delivery.
- [x] Add post-delivery rating/feedback.
- [ ] Verify the page inside WhatsApp's in-app browser and normal mobile
  browsers.
- [ ] Verify refresh, back navigation, expired link, unknown link, and offline
  recovery states.

## 8. WhatsApp Confirmation and Status Updates

- [x] Add the public frontend base URL to backend configuration.
- [x] Build the canonical tracking URL after order creation.
- [x] Replace the tracking-code-only receipt with a clickable tracking link or
  approved URL button.
- [ ] Include order number, selected branch, items, total, payment state, ETA,
  support instructions, and tracking action in the confirmation.
- [ ] Create WhatsApp utility templates for:
  - order placed/received;
  - order accepted;
  - out for delivery;
  - delivered;
  - delayed;
  - rejected/cancelled.
- [ ] Submit the templates for Meta approval.
- [ ] Confirm templates work with the production WhatsApp number.
- [x] Trigger notifications only after the order event is committed.
- [x] Add a `notification_events` table or equivalent persistent outbox.
- [x] Make notification sending idempotent per order event.
- [x] Add retry with backoff for recoverable WhatsApp errors.
- [ ] Record sent, delivered, read, failed, and retry states from WhatsApp
  webhooks where available.
- [x] Ensure notification failure does not erase or revert a valid order update.
- [ ] Route customer replies into a visible support path.
- [ ] Confirm each branch's support identity/contact is shown correctly.

## 9. Kitchen and Branch Dashboard

- [x] Remove demo/no-auth production behavior.
- [x] Implement staff authentication.
- [x] Implement owner, manager, kitchen, dispatch, and support permissions
  needed for launch.
- [x] Scope kitchen users to their assigned branch.
- [x] Allow owners to switch between Ashesi University, Abelemkpe, and a
  combined authorized view.
- [x] Default a kitchen screen to its own branch.
- [x] Add a prominent visual and audible new-order alert.
- [x] Require staff to accept or reject a new order.
- [x] Capture the accepted ETA or preparation estimate.
- [x] Add clear action buttons for:
  - Accept
  - Start preparing
  - Mark ready
  - Send out for delivery
  - Mark delivered
- [x] Require a reason for rejection, cancellation, delay, or exceptional status
  correction.
- [x] Prevent invalid or skipped transitions on both frontend and backend.
- [x] Disable repeated actions while a status mutation is in flight.
- [x] Handle two staff members acting on the same order safely.
- [x] Show customer, address, landmark, phone, branch, items, modifiers, notes,
  payment state, and event history.
- [x] Add branch-specific sold-out controls.
- [x] Add ordering-open/closed controls for each branch.
- [x] Alert staff when a new order has not been accepted within the configured
  threshold.
- [x] Add a controlled WhatsApp notification retry/resend action.
- [x] Audit the staff user and timestamp for every operational action.

## 10. Payment and Delivery Operations

- [x] Add a normalized `payments` table.
- [ ] Integrate the selected Mobile Money/payment provider.
- [ ] Validate payment-provider webhooks.
- [ ] Make webhook processing idempotent.
- [x] Do not mark an order paid from browser input alone.
- [x] Support cash on delivery with a distinct pending/collected state.
- [ ] Show payment failure and retry guidance without duplicating the order.
- [ ] Add payment reconciliation and staff-visible references.
- [ ] Add refund/cancellation handling appropriate to the launch policy.
- [ ] Decide how a rider is assigned.
- [ ] Store customer-safe rider name/phone only when needed.
- [x] Record dispatch and delivery timestamps.
- [ ] Add failed-delivery and customer-unreachable handling.
- [ ] Evaluate Hubtel/Glovo or another provider only if third-party delivery is
  required.
- [ ] Treat live rider GPS as a later enhancement unless real location data is
  available.

## 11. Modern Visual and Convenience Features

- [x] Create a strong mobile-first branch-selection hero.
- [x] Use a consistent visual system across menu, checkout, tracker, and staff
  views.
- [x] Add subtle transitions that clarify state changes without slowing the
  interface.
- [x] Use large tap targets and accessible form controls.
- [ ] Meet useful color-contrast and keyboard-navigation standards.
- [x] Add an installable PWA manifest and icons.
- [x] Add an offline/reconnect message instead of silent failure.
- [x] Add saved customer details on the device with clear privacy behavior.
- [ ] Add lightweight favorites and one-tap reorder after the core journey is
  stable.
- [ ] Add promo/discount support only after backend pricing rules exist.
- [x] Add first-party analytics events for branch selection, menu additions,
  checkout completion, and tracking-page opens.
- [ ] Extend analytics to menu impressions, cart abandonment, repeat orders,
  acceptance time, kitchen time, and delivery time.
- [x] Avoid manipulative countdowns, fake stock warnings, and fabricated ETAs.

## 12. Security, Privacy, and Reliability

- [x] Protect all admin and staff routes.
- [x] Enforce tenant and branch access in backend queries.
- [ ] Enforce matching Supabase RLS policies.
- [ ] Verify Ashesi staff cannot access Abelemkpe-restricted orders and vice
  versa.
- [ ] Use least-privilege Supabase and Meta credentials.
- [x] Keep service-role credentials on the backend only.
- [x] Restrict CORS to approved production and development origins.
- [ ] Verify Meta webhook signatures and add replay protection.
- [x] Add request validation and sensible rate limits.
- [x] Avoid logging full tokens, payment secrets, or unnecessary customer PII.
- [ ] Add structured application logs with order and event correlation IDs.
- [ ] Add error reporting and alerting.
- [ ] Add notification retry monitoring.
- [x] Add database backup and recovery guidance.
- [x] Add health checks for database and WhatsApp dependencies.
- [x] Document incident handling for stuck orders and notification outages.
- [x] Provide a manual support fallback when WhatsApp delivery is unavailable.

## 13. Automated Tests

### Backend

- [x] Test branch listing and customer-safe response fields.
- [x] Test branch-required order creation.
- [ ] Test unknown, inactive, and closed branch rejection.
- [ ] Test branch menu availability and pricing overrides.
- [x] Test backend delivery fee and total calculation.
- [x] Test duplicate-order idempotency.
- [ ] Test every allowed and forbidden status transition.
- [x] Test tracking token lookup and safe response fields.
- [x] Test notification-outbox idempotency and retry behavior.
- [ ] Test payment webhook validation and replay protection.
- [x] Test tenant and branch authorization boundaries.
- [x] Keep all existing backend tests passing.

### Frontend

- [ ] Test branch selection and persistence.
- [ ] Test safe branch switching with a populated cart.
- [ ] Test variant/modifier price display.
- [ ] Test checkout validation and recoverable errors.
- [ ] Test success-to-tracking navigation.
- [ ] Test every pipeline status and exception state.
- [ ] Test realtime update and polling fallback behavior.
- [ ] Test kitchen action permissions and mutation locking.
- [x] Keep the production frontend build passing.

### End-to-end

- [ ] Complete a live Ashesi University test order.
- [ ] Complete a live Abelemkpe test order.
- [ ] Confirm each order reaches only the correct kitchen queue.
- [ ] Confirm each customer receives the correct branch receipt and tracking
  URL.
- [ ] Move each order through the full pipeline and verify the page updates.
- [ ] Confirm WhatsApp stage notifications arrive once.
- [ ] Test delayed, rejected, cancelled, payment-failed, and unavailable-item
  journeys.
- [ ] Test on representative Android devices and an iPhone.
- [ ] Test inside WhatsApp's in-app browser.
- [ ] Test on a slower network profile.

## 14. Deployment and Launch

- [ ] Review and apply database migrations in order.
- [ ] Record the applied migration state.
- [ ] Configure production frontend and backend URLs.
- [ ] Configure Supabase, Meta, payment, monitoring, and support environment
  variables.
- [ ] Verify secrets are not exposed in frontend bundles or repository history.
- [ ] Approve and activate WhatsApp utility templates.
- [ ] Configure the production WhatsApp webhook.
- [ ] Seed both branches and their menus.
- [ ] Create staff accounts and branch memberships.
- [ ] Verify HTTPS and the public tracking domain.
- [ ] Add branch QR codes after canonical URLs are stable.
- [ ] Train staff on accepting, preparing, dispatching, delivering, delaying,
  and cancelling orders.
- [ ] Run at least five internal orders per branch.
- [ ] Run a limited soft launch during staffed operating hours.
- [ ] Monitor order creation, acceptance time, kitchen time, delivery time,
  payment failures, and WhatsApp failures.
- [ ] Document rollback and manual-order procedures.

## 15. Launch Acceptance Gate

Do not call the system production-ready until every statement below is true:

- [ ] A customer can intentionally select Ashesi University or Abelemkpe.
- [ ] The selected branch remains visible throughout the order.
- [ ] The backend validates branch, item availability, price, fee, and total.
- [ ] The correct branch receives the order immediately.
- [ ] Staff must authenticate and are restricted to authorized branches.
- [ ] The customer receives a working private tracking link through WhatsApp.
- [ ] The tracking page shows genuine event-driven progress.
- [ ] Important status changes generate reliable WhatsApp updates.
- [ ] Payment state reflects provider or staff-confirmed reality.
- [ ] Delays, cancellations, failures, and support escalation have usable paths.
- [ ] Both branch journeys pass live end-to-end testing.
- [ ] Monitoring and a manual fallback exist for launch-day failures.

## Later Enhancements

These should not block the dependable two-branch launch:

- [ ] Live rider GPS map.
- [ ] Scheduled ordering.
- [ ] Customer accounts across devices.
- [ ] Loyalty points and rewards.
- [ ] Referral program.
- [ ] Advanced promotions and campaign automation.
- [ ] Native Android/iOS applications.
- [ ] Third-party delivery marketplace integrations.
- [ ] Advanced branch analytics and demand forecasting.

## Research References

- [Domino's Tracker and delivery GPS](https://www.dominos.com/en/about-pizza/gps-tracker/)
- [Toast order-status tracking and customer messages](https://support.toasttab.com/en/article/Toast-Delivery-Services-Order-Status-SMS-Texts)
- [Bolt Food order status stages](https://bolt.eu/en-de/support/articles/360007191560/)
- [WhatsApp utility order messages](https://whatsappbusiness.com/products/conversation-categories/utility/)
- [Hubtel restaurant delivery and real-time tracking](https://explore.hubtel.com/restaurants/)
