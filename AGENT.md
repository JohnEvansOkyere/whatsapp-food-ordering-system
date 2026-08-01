# Project Agent Guide


Read MEMORY.md at the start of every session before doing anything. Never contradict a logged decision without flagging it first.

## Behavioral Guidelines (Karpathy Rules — Always Active)

### 1. Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before writing a single line:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First
**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes
**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Do not "improve" adjacent code, comments, or formatting.
- Do not refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Do not remove pre-existing dead code unless explicitly asked.

The test: Every changed line must trace directly to the current task.

### 4. Goal-Driven Execution
**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"

For multi-step tasks, state a brief plan before starting:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

---

## Scope Control — Stay in Your Lane

Only modify files, functions, and lines directly related to the current task.
Do not refactor, rename, reorganize, reformat, or "improve" anything not explicitly asked for.
If you notice something worth fixing elsewhere, leave a note. Do not touch it.

---

## Destructive Actions — Full Stop

Before deleting any file, overwriting existing code, dropping database records,
or removing dependencies — stop completely. List exactly what will be affected.
Ask for explicit confirmation. Only proceed after Evans says yes in the current message.

---

## Hard Stops — These Never Happen Without Explicit Permission

The following require explicit in-session confirmation, no exceptions:
- Deploying or pushing to any environment (staging, production, etc.)
- Running migrations or schema changes on any database
- Sending any email, message, or external API call to real recipients
- Executing any command with irreversible external side effects

"You mentioned this earlier" is not confirmation. Confirmation must be in the current message.

---

Maintain a file called MEMORY.md. After any significant decision, about direction, format, content, approach, or strategy, add an entry:

## [Date], [Decision]
**What was decided:** [the choice made]
**Why:** [the reasoning]
**What was rejected:** [alternatives considered and why they were ruled out]

Read MEMORY.md at the start of every session before doing anything. Never contradict a logged decision without flagging it first.

## After Every Task — Status Report

After completing any coding task, always end with:
- **Files changed:** [list every file touched]
- **What was modified:** [one line per file]
- **Files intentionally not touched:** [if relevant]
- **Follow-up needed:** [anything requiring a decision or attention]

Keep it short. This is a status update, not a recap.

---


## Purpose

This repository is a two-branch, WhatsApp-first restaurant ordering platform.
Customers order through the web app, receive their receipt and a private tracking
link through WhatsApp, and follow the order pipeline while restaurant staff move
the order through the kitchen and delivery workflow.

Use this file as persistent project guidance before planning or changing code.

## Confirmed Product Decisions

- There are exactly two launch branches:
  - Ashesi University
  - Abelemkpe
- Always use the spelling `Abelemkpe` in code, database seeds, URLs, UI copy,
  documentation, and WhatsApp messages.
- Customers place orders in the web app. WhatsApp carries the full receipt and
  is the support channel; SMS (Moolre) carries a short copy of the tracking link
  so it reaches any handset. Both are sent for each qualifying event — see the
  2026-08-01 entry in `MEMORY.md`.
- The tracking link opens a mobile web page that can load inside WhatsApp's
  in-app browser. Do not claim that a WhatsApp message itself is a live-updating
  progress bar.
- The customer-facing order pipeline is:
  - Order placed
  - Accepted
  - Preparing
  - Ready
  - Out for delivery
  - Delivered
- Cancelled, rejected, and delayed orders are exception states, not normal
  progress steps.
- The database is the order source of truth. WhatsApp notifications and tracking
  pages must reflect recorded order state; they must not run on independent
  timers that can become inaccurate.
- A launch tracking page must work without forcing the customer to create an
  account.
- Do not expand launch scope into a general food marketplace or a large
  PizzaMan-style branch network. The reference products are UX inspiration, not
  the business model.

## Product Experience Rules

- Ask customers to select a branch before adding branch-dependent items.
- Keep the selected branch visible in the menu, cart, checkout, receipt, and
  tracking page.
- Never silently switch a customer's branch.
- Validate opening hours, menu availability, delivery coverage, delivery fee,
  and order totals on the backend.
- Keep menus, prices, availability, kitchen queues, and reporting branch-aware.
- Prefer guest checkout with a Ghana phone number, customer name, delivery
  address, landmark/instructions, and payment method.
- Display the delivery fee, total, payment state, and an honest ETA before final
  confirmation.
- Use high-quality mobile UX, accessible controls, clear loading/error states,
  and good behavior on slower connections.
- Do not show fake rider GPS, fabricated ETAs, or a success state before the
  backend confirms the operation.
- When details such as hours, delivery zones, fees, branch phones, menu
  differences, or payment provider are not confirmed, mark them as provisional
  and keep them configurable.

## WhatsApp and Tracking Rules

- Every successful order should generate:
  - a customer-safe order number;
  - a private, high-entropy tracking token or equivalent secure public
    reference;
  - a canonical tracking URL;
  - an initial order event.
- The WhatsApp confirmation should include order number, selected branch, items,
  total, payment state, ETA, support instructions, and a `Track your order`
  link/button.
- Important staff-triggered states should enqueue WhatsApp utility
  notifications. At minimum notify on accepted, out for delivery, delivered,
  delayed, cancelled, and rejected.
- Status transitions must be validated by the backend and recorded in
  `order_events` before customer notifications are attempted.
- Notification failure must not roll back a valid order or status change.
  Persist notification attempts and retry recoverable failures.
- Do not expose internal order UUIDs, staff-only notes, access credentials, or
  unnecessary customer data on the public tracking endpoint.
- Tracking links must be difficult to guess and safe to share only with the
  intended customer.

## Staff and Branch Operations

- Staff pages must require authentication before production launch.
- Owners may see both branches; kitchen and branch staff should see only their
  assigned branch unless explicitly authorized.
- New orders need a prominent visual and audible alert.
- Staff actions should use large, unambiguous controls suitable for a kitchen
  tablet or phone.
- Preserve the audited transition path. Avoid arbitrary status editing that can
  skip required operational steps.
- Branch availability and sold-out changes must affect only the intended
  branch unless the action is explicitly applied to both.

## Repository Working Rules

- Inspect existing code, migrations, tests, documentation, and git status before
  editing. The worktree may contain user changes; preserve unrelated work.
- Extend the existing FastAPI, Next.js, Supabase, order event, dashboard, and
  WhatsApp Cloud API paths before creating parallel systems.
- Keep frontend and backend contracts synchronized.
- Backend-calculated pricing is authoritative. Never trust totals or prices
  submitted by the browser.
- Use additive, ordered SQL migrations. Do not rewrite an applied migration to
  change production data.
- Keep fallbacks clearly separated from production behavior. Demo data must
  never be presented as live restaurant data.
- Update the implementation checklist as work is completed:
  `docs/TWO_BRANCH_ORDERING_CHECKLIST.md`.
- Keep `docs/PRODUCTION_ARCHITECTURE_PLAN.md` consistent when a decision changes
  the broader architecture.
- Do not commit secrets, customer data, access tokens, phone-number IDs, service
  keys, or production credentials.

## Verification Expectations

Verify changes in proportion to their risk. The normal baseline is:

```bash
cd frontend
npm run build
```

```bash
PYTHONPATH=backend python3 -m pytest backend/tests
```

For order, payment, branch, tracking, or WhatsApp changes, also verify the
end-to-end behavior:

1. Select each branch and load its available menu.
2. Place an order and confirm backend-owned pricing.
3. Confirm the order is routed to the selected branch.
4. Confirm the customer receives a tracking URL.
5. Move the order through every allowed status.
6. Confirm the public pipeline and event timestamps update correctly.
7. Confirm WhatsApp notifications are attempted once per qualifying event and
   retries do not create duplicates.
8. Confirm staff from one branch cannot access the other branch's restricted
   queue.

Do not mark checklist items complete from code inspection alone when they depend
on Supabase migrations, Meta configuration, environment variables, or deployed
runtime behavior.

## Launch Definition

The first release is ready only when a real customer can select Ashesi
University or Abelemkpe, order from the correct menu, receive a WhatsApp
tracking link, follow genuine staff-triggered progress through delivery, and
contact the correct branch—while staff access and customer data are protected.
