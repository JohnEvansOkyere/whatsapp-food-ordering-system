# Production Architecture Plan
**WhatsApp Food Ordering Platform**

This document is the working architecture and delivery plan for turning the current project into a production-grade restaurant operations platform.

It is intended to be updated continuously:
- Keep checkboxes current as work is completed
- Add links to relevant PRs, files, migrations, and deployments
- Record architecture decisions here before large changes are made

## 1. Product Goal

Build a high-reliability restaurant ordering and customer-service platform that supports:
- customer ordering via web and WhatsApp
- internal staff order management without going into Supabase directly
- live order tracking and customer updates
- cancellation and refund-aware order flows
- multi-tenant support for many restaurants
- branch support for restaurants with multiple locations
- role-based access for owners, managers, kitchen, dispatch, and support staff

This system should feel like a typical modern restaurant service desk:
- fast to operate
- clear to staff
- trackable by customers
- auditable by owners
- safe to scale

## 2. Target System Principles

- Single source of truth: Postgres/Supabase is the operational system of record
- Operational first: dashboard, workflows, and auditability matter more than AI flair
- AI is bounded: AI helps with language and assistance, but business rules stay deterministic
- Multi-tenant by design: every important record is tenant-aware
- Branch-aware operations: order routing and staff visibility must support branches
- Observable and recoverable: failures should be logged, traceable, and retryable
- Presentable to clients: system must look and behave like a real business platform

## 3. High-Level Architecture

```text
Customer Channels
  - Web ordering app
  - WhatsApp chat ordering
  - Order tracking page
          |
          v
Application Layer
  - Public API
  - Admin API
  - Authentication / authorization
  - Order orchestration
  - Notification orchestration
          |
          v
Core Domain Services
  - Tenant service
  - Branch service
  - Menu service
  - Order service
  - Customer service
  - Conversation service
  - Reporting service
  - Integration service
          |
          v
Data + Infrastructure
  - Supabase/Postgres
  - Redis for session/state/cache
  - Object storage for assets
  - Background jobs / task queue
  - Monitoring + logs
          |
          v
External Integrations
  - WhatsApp Cloud API
  - Google Sheets sync
  - Mobile Money / payments
  - Email / SMS / analytics
```

## 4. Product Modules

### Public / Customer-facing
- Menu browsing
- Cart and checkout
- WhatsApp-assisted ordering
- Order confirmation
- Order tracking
- Customer cancellation requests
- Reorder experience

### Staff / Admin-facing
- Live order queue
- Order details panel
- Status update controls
- Cancellation management
- Customer contact shortcuts
- Branch filtering
- Role-aware dashboard views
- Sales and order reporting

### Platform / Internal
- Tenant management
- Branch provisioning
- User and role management
- Integration setup
- audit logs
- billing and subscription controls

## 5. Core Business Entities

The long-term data model should be organized around these core entities:

- `tenants`
- `branches`
- `users`
- `roles`
- `user_branch_memberships`
- `customers`
- `menus`
- `menu_items`
- `orders`
- `order_items`
- `order_events`
- `payments`
- `conversations`
- `messages`
- `integrations`
- `webhook_events`
- `notification_events`

### Required tenancy keys

The following tables should be tenant-scoped:
- `branches`
- `users`
- `customers`
- `menu_items`
- `orders`
- `order_items`
- `order_events`
- `payments`
- `conversations`
- `integrations`

Recommended keys:
- `tenant_id` on all tenant-owned records
- `branch_id` on branch-specific records
- `created_by` / `updated_by` on staff-generated actions where relevant

## 6. Multitenant Model

### Target structure
- One platform serves many restaurant businesses
- Each restaurant business is a `tenant`
- Each restaurant can have one or many `branches`
- Staff belong to a tenant and can be scoped to one or more branches

### Isolation requirements
- staff from Tenant A must never see Tenant B data
- branch users should only see their permitted branches
- platform admins can view across tenants
- all queries, APIs, and policies must enforce tenant scoping

### Recommended enforcement
- tenant-aware JWT claims
- role checks in backend services
- Supabase RLS policies aligned with tenant and branch membership
- no client-side trust for access control

### Final design decision

The platform will use a strict `tenant -> branch -> user access` model.

- `tenant` = a restaurant business account
- `branch` = a physical or operational restaurant location under that tenant
- `user` = an authenticated staff member or owner
- `membership` = the role and branch scope a user has inside a tenant

### Tenant ownership rules

- every restaurant-operated record must belong to exactly one `tenant`
- every operational record that is branch-specific must also belong to one `branch`
- a branch cannot exist without a parent tenant
- users can belong to one tenant at first release
- platform admins exist outside tenant restrictions and are internal-only

### Required first-release tables

#### `tenants`
- `id`
- `name`
- `slug`
- `status`
- `subscription_plan`
- `default_currency`
- `default_timezone`
- `created_at`
- `updated_at`

#### `branches`
- `id`
- `tenant_id`
- `name`
- `code`
- `phone`
- `address`
- `city`
- `country`
- `is_default`
- `is_active`
- `opening_hours_json`
- `created_at`
- `updated_at`

#### `users`
- `id`
- `tenant_id`
- `email`
- `full_name`
- `phone`
- `status`
- `last_login_at`
- `created_at`
- `updated_at`

#### `user_branch_memberships`
- `id`
- `tenant_id`
- `user_id`
- `branch_id`
- `role_code`
- `is_primary`
- `created_at`
- `updated_at`

#### `orders`
- `id`
- `tenant_id`
- `branch_id`
- `customer_id`
- `order_number`
- `channel`
- `status`
- `payment_status`
- `fulfillment_type`
- `subtotal_amount`
- `delivery_fee`
- `discount_amount`
- `total_amount`
- `currency`
- `customer_name_snapshot`
- `customer_phone_snapshot`
- `delivery_address_snapshot`
- `notes`
- `placed_at`
- `confirmed_at`
- `delivered_at`
- `cancelled_at`
- `created_at`
- `updated_at`

#### `order_items`
- `id`
- `tenant_id`
- `branch_id`
- `order_id`
- `menu_item_id`
- `item_name_snapshot`
- `unit_price`
- `quantity`
- `line_total`
- `special_instructions`
- `created_at`

#### `order_events`
- `id`
- `tenant_id`
- `branch_id`
- `order_id`
- `event_type`
- `from_status`
- `to_status`
- `actor_type`
- `actor_user_id`
- `actor_label`
- `reason_code`
- `reason_note`
- `metadata_json`
- `created_at`

### Table migration direction

- keep `orders.items` temporarily only for backward compatibility during migration
- target normalized `order_items` as the durable long-term model
- snapshot customer name, phone, and delivery address on the order even if customer profile changes later
- snapshot menu item name and price on `order_items` so old orders remain historically correct

### Tenant resolution strategy

#### Public web ordering
- tenant is resolved from domain, subdomain, or deployment configuration
- branch is resolved from selected branch, query parameter, or tenant default branch

#### WhatsApp ordering
- tenant and branch are resolved from the incoming WhatsApp number, referral payload, or configured branch mapping
- QR or direct WhatsApp links should carry a branch reference where possible

#### Admin dashboard
- tenant comes from authenticated user context
- visible branches come from membership records

### First-release access constraints

- one user belongs to one tenant only
- one tenant can have many branches
- one user can belong to many branches inside the same tenant
- one order belongs to one branch only
- one menu item can be tenant-global or branch-scoped

### RLS implementation direction

- all tenant-owned tables must filter on `tenant_id`
- branch-scoped tables must additionally filter on allowed branch membership
- writes must validate both tenant match and branch membership
- service-role backend paths may bypass RLS only for trusted server operations

### Query and API rules

- every admin API must derive tenant from auth, never from raw user input
- branch filters from the client must be intersected with allowed branch memberships
- public APIs must never expose cross-tenant IDs or enumerations
- internal IDs can remain UUIDs; client-facing order references should use shorter branch-safe order numbers

### Open implementation notes

- decide whether auth is fully handled by Supabase Auth or by a separate auth layer with Supabase as data store
- decide whether each tenant gets a custom domain at first release or later release
- decide whether menu items are copied per branch or inherited with branch overrides

## 7. Role Model

Initial production roles:

- `platform_admin`
  - internal super admin across all tenants
- `tenant_owner`
  - full control over one restaurant business
- `manager`
  - manages branches, orders, staff, and reports
- `cashier`
  - creates and updates customer orders
- `kitchen`
  - handles accepted, preparing, and ready workflows
- `dispatch`
  - handles ready, out-for-delivery, and delivered workflows
- `support`
  - handles customer communication and issue resolution
- `viewer`
  - read-only access to operational and reporting views

### Final design decision

Roles will be enforced as capability bundles, not only labels.
Each role maps to a fixed set of permissions, and permissions are evaluated on:
- tenant scope
- branch scope
- action type

### Permission groups

Core permission groups for first release:
- `orders.read`
- `orders.create`
- `orders.update`
- `orders.cancel`
- `orders.assign`
- `orders.export`
- `customers.read`
- `customers.update`
- `menu.read`
- `menu.update`
- `reports.read`
- `branches.read`
- `branches.update`
- `staff.read`
- `staff.manage`
- `settings.manage`
- `integrations.manage`

### Role definitions

#### `platform_admin`
- full access across all tenants
- can impersonate tenant views for support
- can manage tenant lifecycle, subscriptions, and internal diagnostics

#### `tenant_owner`
- full access within one tenant
- can manage branches, staff, settings, reports, and integrations
- can override cancellation decisions and operational blocks

#### `manager`
- full operational access within assigned branches
- can manage orders, cancellations, branch-level staff, and branch reports
- cannot manage billing or platform-level configuration

#### `cashier`
- can create orders
- can view and update order details within assigned branches
- can confirm incoming orders
- can request or perform cancellation before kitchen preparation depending on policy
- cannot manage tenant settings or staff

#### `kitchen`
- can read confirmed and active kitchen orders within assigned branches
- can move orders from `confirmed` to `preparing` to `ready`
- cannot cancel delivered orders
- cannot access financial settings or staff management

#### `dispatch`
- can read ready and active delivery orders within assigned branches
- can move orders from `ready` to `out_for_delivery` to `delivered`
- can contact customers for delivery coordination
- cannot edit menus or manage staff

#### `support`
- can read orders and customer records within assigned branches
- can log issues, contact customers, and request cancellation workflows
- can create support notes and escalation events
- cannot directly change sensitive settings unless separately granted

#### `viewer`
- read-only visibility for allowed branches
- can view order history and reports
- cannot create or modify operational data

### Recommended first-release permission matrix

| Role | Read Orders | Update Status | Cancel Order | View Reports | Manage Staff | Manage Settings |
|---|---|---|---|---|---|---|
| `platform_admin` | Yes | Yes | Yes | Yes | Yes | Yes |
| `tenant_owner` | Yes | Yes | Yes | Yes | Yes | Yes |
| `manager` | Yes | Yes | Yes | Yes | Limited | No |
| `cashier` | Yes | Limited | Limited | No | No | No |
| `kitchen` | Yes | Kitchen states only | No | No | No | No |
| `dispatch` | Yes | Delivery states only | No | No | No | No |
| `support` | Yes | Limited by workflow | Request only | Limited | No | No |
| `viewer` | Yes | No | No | Yes | No | No |

### Branch scoping rules

- `tenant_owner` sees all branches in that tenant
- `manager` can be assigned to one or more branches
- `cashier`, `kitchen`, `dispatch`, `support`, and `viewer` must be branch-scoped by default
- branch-scoped users must never see orders from branches they are not assigned to

### Sensitive action rules

The following actions should always be audited:
- cancellation approval
- order rejection
- delivery completion override
- menu price changes
- branch settings changes
- staff invitation and role changes

The following actions should require owner or manager capability:
- cancel order after kitchen has started preparing
- mark refunds or payment overrides
- modify branch configuration
- manage staff accounts
- connect external integrations

### UI implications

- dashboard navigation should hide features the user cannot access
- disabled actions should still explain why they are blocked
- the order details view should render action buttons according to role and order state
- branch switchers should only show authorized branches

### Future role extension path

If needed later, add:
- `finance`
- `marketing`
- `franchise_admin`
- `driver`

Do not add extra roles until a real operational need appears.

## 8. Order Lifecycle

The order lifecycle should be explicit and policy-driven.

Recommended statuses:
- `new`
- `confirmed`
- `preparing`
- `ready`
- `out_for_delivery`
- `delivered`
- `cancel_requested`
- `cancelled`
- `rejected`

### Rules
- all status changes must be validated on the backend
- invalid state jumps should be blocked
- cancellation rules should depend on current state
- customer-facing messages should be triggered by state changes
- every state change should create an `order_event`

### Order event examples
- order_created
- order_confirmed
- order_preparing
- order_ready
- order_dispatched
- order_delivered
- cancellation_requested
- order_cancelled
- refund_marked
- customer_contacted

### Final design decision

The order lifecycle will be enforced as a backend state machine.
Frontend clients and AI assistants may request transitions, but only backend policy can approve them.

### Canonical statuses

#### `new`
- order has been created and is awaiting staff acknowledgement

#### `confirmed`
- restaurant has accepted the order and committed to fulfill it

#### `preparing`
- kitchen or prep team has started working on the order

#### `ready`
- order is complete and ready for pickup or dispatch

#### `out_for_delivery`
- order has left the branch and is on the way to the customer

#### `delivered`
- order has been successfully completed

#### `cancel_requested`
- customer or staff has requested cancellation, but approval is pending

#### `cancelled`
- order has been cancelled and will not be fulfilled

#### `rejected`
- restaurant declined the order before confirmation

### Allowed status transitions

| From | Allowed To |
|---|---|
| `new` | `confirmed`, `rejected`, `cancel_requested`, `cancelled` |
| `confirmed` | `preparing`, `cancel_requested`, `cancelled` |
| `preparing` | `ready`, `cancel_requested` |
| `ready` | `out_for_delivery`, `delivered`, `cancel_requested` |
| `out_for_delivery` | `delivered`, `cancel_requested` |
| `cancel_requested` | `cancelled`, `confirmed`, `preparing`, `ready`, `out_for_delivery` |
| `rejected` | no forward transitions |
| `cancelled` | no forward transitions |
| `delivered` | no forward transitions |

### Transition policy notes

- `new -> cancelled` is allowed for immediate customer cancellation before staff action
- `new -> rejected` is restaurant-driven refusal before commitment
- `confirmed -> cancelled` is allowed only for manager-level roles or automated policy exceptions
- `preparing -> cancel_requested` is allowed, but direct cancellation should require manager approval
- `ready -> delivered` is allowed for walk-in pickup or branch handoff flows
- `cancel_requested` acts as a holding state while a human decision is made

### Cancellation policy

#### Customer policy
- customers can cancel freely while order is `new`
- customer cancellation after `confirmed` becomes a request, not an automatic cancellation
- customer cancellation after `preparing` requires staff approval
- customer cancellation after `out_for_delivery` should default to denied unless there is an exception case

#### Staff policy
- cashier can cancel while order is `new`
- manager or tenant owner can cancel while order is `confirmed`
- manager approval is required once order is `preparing` or later
- delivered orders cannot be cancelled; they can only be handled through issue or refund workflows

#### Cancellation data requirements
- every cancellation or cancellation request must store a `reason_code`
- free-text `reason_note` should be optional but supported
- actor identity must be recorded
- customer notification must be sent after a final decision

### Recommended reason codes

- `customer_changed_mind`
- `duplicate_order`
- `out_of_stock`
- `branch_overloaded`
- `payment_failed`
- `invalid_address`
- `customer_unreachable`
- `delivery_issue`
- `fraud_suspected`
- `other`

### Service-level expectations

- `new` orders should be acknowledged quickly in the dashboard
- `confirmed` orders should include a visible promised prep or delivery estimate
- stale orders should be flagged if they remain too long in one state
- dashboard should surface overdue and exception orders separately

### Customer messaging expectations

These messages should be automatic:
- order received
- order confirmed
- order being prepared
- order out for delivery
- order delivered
- cancellation requested received
- order cancelled
- order rejected

### Required audit fields on transition

Every status transition should record:
- `order_id`
- `from_status`
- `to_status`
- `actor_type`
- `actor_user_id` when available
- `reason_code` when applicable
- `reason_note` when applicable
- `created_at`

### Delivery and pickup extension

For later releases, `fulfillment_type` should shape lifecycle behavior:
- `delivery`
- `pickup`
- `dine_in`

At first release:
- prioritize `delivery`
- allow `pickup` if the UI and notifications are ready
- defer `dine_in` until there is a clear business need

## 9. API Boundary

The platform should be split into clearly separated API surfaces.

### Final design decision

Use separate public and admin API domains within the same backend application first, with the option to split them physically later.

Recommended route families:
- `/public/*`
- `/admin/*`
- `/internal/*`
- `/webhooks/*`

This gives clean separation of concerns without forcing early microservice complexity.

### Public API scope

The public API serves customers and unauthenticated client applications.

Allowed responsibilities:
- fetch public tenant and branch context
- fetch active menu and availability
- create customer orders
- fetch customer-safe order tracking data
- create customer cancellation requests
- submit reorder intents

Public API rules:
- must never expose staff-only data
- must be rate-limited
- must use customer-safe response shapes
- must validate tenant and branch context on every request
- must not trust any client-supplied totals without backend recomputation

### Admin API scope

The admin API serves authenticated restaurant staff and owners.

Allowed responsibilities:
- list and filter orders
- view order details and audit history
- update statuses
- resolve cancellation requests
- manage branches, menus, staff, and settings
- access reports and exports
- manage integrations

Admin API rules:
- requires authenticated user context
- derives `tenant_id` from auth, not request payload
- enforces branch permissions for every read and write
- returns richer operational data than the public API
- all sensitive mutations create audit events

### Internal API scope

The internal API is for trusted server-to-server operations only.

Allowed responsibilities:
- background job callbacks
- integration sync handlers
- webhook post-processing
- reconciliation jobs
- internal diagnostics

Internal API rules:
- never exposed to browsers as a general client surface
- protected with service credentials or signed internal auth
- all calls are logged with source identity

### Webhook API scope

Webhook endpoints are isolated because they receive traffic from external providers.

Initial webhooks:
- WhatsApp message webhooks
- delivery partner webhooks later
- payment provider webhooks later
- Google Sheets callback endpoints only if needed later

Webhook rules:
- validate signatures where provider supports it
- store raw payload and normalized event record
- process asynchronously where possible
- ensure idempotency on retries

### Recommended first-release endpoint map

#### Public
- `GET /public/tenant-context`
- `GET /public/menu`
- `POST /public/orders`
- `GET /public/orders/{tracking_code}`
- `POST /public/orders/{tracking_code}/cancel-request`

#### Admin
- `GET /admin/orders`
- `GET /admin/orders/{order_id}`
- `PATCH /admin/orders/{order_id}/status`
- `POST /admin/orders/{order_id}/cancel`
- `GET /admin/orders/{order_id}/events`
- `GET /admin/dashboard/summary`
- `GET /admin/branches`
- `GET /admin/customers/{customer_id}`

#### Internal
- `POST /internal/notifications/order-status-changed`
- `POST /internal/integrations/google-sheets/sync-order`
- `POST /internal/jobs/reconcile-payments`

#### Webhooks
- `GET /webhooks/whatsapp`
- `POST /webhooks/whatsapp`

### Response-shape rules

- public responses should expose `tracking_code`, not internal raw IDs where avoidable
- admin responses may use internal UUIDs and richer linked objects
- status responses should always include current state, allowed next actions, and timestamps where relevant
- write responses should include both updated entity data and mutation metadata when useful

### Order creation contract

For production safety, order creation should follow these rules:
- client sends selected items, quantities, customer details, and branch context
- backend re-fetches canonical menu prices and computes totals
- backend writes `orders`, `order_items`, and an initial `order_event`
- backend returns `order_id`, `tracking_code`, current status, and customer-facing summary

### Tracking contract

Customer order tracking should expose only safe fields:
- `tracking_code`
- `status`
- `status_label`
- `placed_at`
- `estimated_ready_at` or `estimated_delivery_at`
- limited branch contact details
- a customer-safe timeline

Tracking must not expose:
- internal audit notes
- staff identities unless explicitly intended
- cross-order search or enumeration capability
- other customer information

### Admin list contract

The admin order list endpoint should support:
- branch filter
- status filter
- date range filter
- payment status filter
- channel filter
- search by order number, phone, or customer name
- pagination or cursoring
- summary counts for active statuses

### Authentication direction

Recommended first release:
- use Supabase Auth for staff authentication
- use backend-validated access tokens for admin APIs
- keep public APIs unauthenticated but tenant-aware and rate-limited
- use service credentials only for trusted internal operations

### Versioning direction

- start with `/public` and `/admin` without a version segment if velocity matters
- adopt `/v1/public` and `/v1/admin` once contracts stabilize or external clients multiply
- breaking contract changes must be recorded in this document before implementation

## 10. Database Migration Plan

The migration strategy should move the current single-restaurant schema into a multitenant operational schema without breaking the live order flow.

### Final design decision

Use additive migrations first, then compatibility reads, then controlled cutover, then cleanup.

Do not do a destructive rewrite in one step.

### Current-state issues to solve

- `orders` is not fully tenant-aware
- `orders.items` is denormalized JSON
- there is no `tenants` table
- there is no `branches` table with enforced relationships
- there is no `order_events` audit trail
- staff auth and role tables do not exist

### Migration phases

#### Phase A: introduce tenancy foundations
- create `tenants`
- create `branches`
- create `users`
- create `user_branch_memberships`
- add `tenant_id` and `branch_id` columns to current operational tables
- create a default seed tenant and branch for the current deployment

#### Phase B: normalize order data
- create `order_items`
- create `order_events`
- add customer and pricing snapshot columns to `orders`
- backfill existing `orders.items` rows into `order_items`
- create initial `order_created` events for historical orders if feasible

#### Phase C: auth and authorization readiness
- introduce staff user records mapped to auth identities
- prepare RLS policies for tenant and branch isolation
- add indexes needed for filtered admin order queries

#### Phase D: API cutover
- update backend writes to create normalized order rows and event rows
- keep compatibility reads during transition
- update admin endpoints to read from normalized schema
- update customer tracking to use `tracking_code` and event-driven status history

#### Phase E: cleanup
- remove dependency on `orders.items`
- tighten nullability and foreign key constraints
- enforce transition-safe and tenant-safe constraints
- remove obsolete compatibility code

### First-release migration assumptions

- assume one existing restaurant deployment maps to one initial tenant
- assume one default branch exists initially
- treat all existing orders as belonging to that default branch
- preserve historical totals even if future menu pricing changes

### Required schema additions

#### Orders
- add `tenant_id`
- add `branch_id`
- add `customer_id`
- add `order_number`
- add `tracking_code`
- add `channel`
- add `payment_status`
- add `fulfillment_type`
- add `subtotal_amount`
- add `delivery_fee`
- add `discount_amount`
- add `currency`
- add `customer_name_snapshot`
- add `customer_phone_snapshot`
- add `delivery_address_snapshot`
- add `placed_at`
- add `confirmed_at`
- add `delivered_at`
- add `cancelled_at`

#### Customers
- add `tenant_id`
- optionally add `default_branch_id`
- add customer metadata fields only when there is a real use case

#### Menu items
- add `tenant_id`
- optionally add nullable `branch_id` to support branch-specific overrides
- add availability controls if branch-level stock handling is planned

### Indexing direction

Recommended early indexes:
- `orders (tenant_id, branch_id, created_at desc)`
- `orders (tenant_id, branch_id, status, created_at desc)`
- `orders (tenant_id, customer_phone_snapshot)`
- `orders (tenant_id, order_number)`
- `orders (tenant_id, tracking_code)`
- `order_events (tenant_id, order_id, created_at)`
- `user_branch_memberships (tenant_id, user_id, branch_id)`
- `menu_items (tenant_id, branch_id, active)`

### Compatibility strategy

During transition:
- write new normalized data and old JSON data if needed temporarily
- read from normalized tables first when available
- fall back to old structures only where necessary
- keep compatibility period as short as possible

### Data backfill rules

- generate one default tenant and branch for current data
- backfill `tenant_id` and `branch_id` on all existing orders
- map existing order item JSON into `order_items`
- generate `tracking_code` and `order_number` for existing orders if needed
- backfill customer snapshots from existing order data

### Constraint direction

After backfill is verified:
- make `tenant_id` non-null on tenant-owned tables
- make `branch_id` non-null on branch-scoped tables
- add foreign keys with cascade rules chosen carefully
- add uniqueness rules such as:
  - unique tenant slug
  - unique branch code within tenant
  - unique order number within tenant or branch
  - unique tracking code globally or tenant-scoped depending UX choice

### Recommended migration ownership

- SQL migrations should be explicit and versioned
- backend compatibility changes should land before destructive cleanup
- dashboard reads should move only after normalized write paths are proven
- production data validation queries should be prepared before each cutover step

### Rollout checks

Before cutover:
- confirm all existing orders have tenant and branch values
- confirm normalized item counts match old JSON counts
- confirm order totals still match historical values
- confirm order creation writes both header and line items
- confirm order events are created on every mutation

After cutover:
- monitor write failures
- monitor missing event creation
- monitor dashboard query latency
- monitor authorization failures by role and branch

## 11. Customer Service Model

This system should behave like a proper restaurant customer-service desk.

### Customer actions
- place an order
- receive confirmation
- track order progress
- request cancellation
- ask questions through WhatsApp
- reorder previous meals

### Staff actions
- accept or reject incoming orders
- update preparation progress
- contact the customer
- approve or deny cancellation
- mark delivery completion
- see order history and issues

### Customer communication channels
- WhatsApp order confirmation
- WhatsApp status updates
- optional web tracking page
- escalation to human staff when AI confidence is low or policy requires it

## 12. AI / Agent Architecture

The correct production approach is:
- one primary customer-facing assistant
- deterministic backend workflows
- bounded tools for operational actions

### Recommended assistant responsibilities
- greet naturally
- answer menu questions
- recommend menu items
- help collect order details
- confirm items, total, address, and payment
- escalate exceptions to staff

### Recommended non-AI responsibilities
- order creation
- status transition validation
- cancellation policy
- payment rules
- branch routing
- user permissions
- audit trail creation

### Scaling recommendation
Start with a single orchestrated assistant.

Do not start with multiple autonomous agents for restaurant operations.
Multiple agents can be considered later only if there is a clear operational boundary such as:
- customer assistant
- staff copilot
- analytics assistant

Even then, all of them must operate through the same permissioned backend tools.

## 13. Admin Dashboard Requirements

The first serious admin dashboard should include:

- live order queue
- filters by branch, status, payment method, and date
- order detail drawer or panel
- status update controls
- cancellation controls with reason capture
- customer phone and WhatsApp shortcut
- order timeline / audit history
- daily totals and summary cards
- search by order ID, phone number, and customer name

### Phase 2 dashboard enhancements
- branch performance view
- staff activity logs
- issue flags and exception queue
- export and reporting
- kitchen display mode
- delivery board

## 14. Google Sheets Integration Strategy

Google Sheets should be an optional integration, not the primary operational system.

### Good uses
- append new orders for owners
- append status changes
- daily revenue summaries
- lightweight exports
- backup visibility for non-technical clients

### Bad uses
- primary status management
- concurrency-sensitive updates
- permissions and audit enforcement
- workflow orchestration

Decision:
- Backend database remains source of truth
- Google Sheets acts as a mirrored reporting layer

## 15. Reliability Requirements

Production baseline requirements:

- idempotent order creation
- webhook signature validation
- retry-safe external message delivery
- failure logging with correlation IDs
- background task retries
- durable session store
- monitoring and alerting
- graceful degradation when AI provider fails

### Current gaps to address
- in-memory session store should move to Redis
- operational dashboard is missing
- audit trail is missing
- tenant and role enforcement is missing
- customer tracking flow is incomplete

## 16. Security Requirements

- role-based access control on all admin endpoints
- tenant-aware row-level security
- secure secret management
- protected admin routes
- action audit logs
- rate limiting for public endpoints
- webhook validation and replay protection
- least-privilege integration credentials

## 17. Recommended Delivery Phases

### Phase 0: Architecture Foundation
- [x] confirm target multi-tenant model
- [x] confirm role model and branch permissions
- [x] confirm final order lifecycle and cancellation rules
- [x] document API boundary between public and admin systems

### Phase 1: Data Model Hardening
- [x] add `tenants` table
- [x] add `branches` table
- [x] add tenant and branch keys to operational tables
- [x] split `orders.items` JSON into normalized `order_items`
- [x] add `order_events` audit table
- [ ] add `payments` table
- [x] create migration plan for existing data

### Phase 2: Auth and Access Control
- [ ] implement admin authentication
- [ ] implement role and branch membership model
- [ ] enforce tenant isolation in backend
- [ ] implement Supabase RLS policies for tenant-safe access
- [ ] protect admin routes in frontend

### Phase 3: Order Operations
- [x] build order list endpoint for staff
- [x] build order detail endpoint with history
- [x] build status update endpoint with transition validation
- [x] build cancellation endpoint with reason capture
- [x] build customer tracking endpoint
- [ ] add automated customer notifications for status updates

### Phase 4: Admin Dashboard
- [x] build live order queue page
- [x] build branch and status filters
- [x] build order detail view
- [x] build status action controls
- [x] build cancellation workflow UI
- [x] build summary cards and search

### Phase 5: Customer Service Improvements
- [ ] move session store to Redis
- [ ] improve returning customer memory
- [ ] add human escalation path
- [ ] add customer order tracking page
- [ ] add reorder shortcuts

### Phase 6: Integrations
- [ ] add Google Sheets mirror sync
- [ ] add delivery/provider integration abstraction
- [ ] add payment integration abstraction
- [ ] add reporting/export jobs

### Phase 7: Reliability and Operations
- [ ] add background job processing
- [ ] add structured logs and error reporting
- [ ] add health checks for critical dependencies
- [ ] add retry strategy for WhatsApp sends
- [ ] add monitoring dashboards and alerts
- [ ] add backup and incident runbook

### Phase 8: Sales Readiness
- [ ] prepare demo tenant data
- [ ] prepare polished admin dashboard flow
- [ ] prepare customer tracking demo flow
- [ ] prepare restaurant onboarding checklist
- [ ] prepare pricing, packaging, and support model

## 18. Immediate Priority Checklist

These are the highest-value items for the next working sessions:

- [x] finalize target architecture decisions in this document
- [x] design multitenant database changes
- [x] define order status transitions and cancellation rules
- [x] define role permissions matrix
- [x] build first admin dashboard for live orders
- [x] add order event audit trail
- [x] add customer tracking updates
- [ ] add Google Sheets mirror after dashboard foundation is stable

## 19. Decision Log

Use this section to record architecture decisions as they are made.

### Decisions
- [x] Database is the primary source of truth
- [x] Google Sheets is a mirrored reporting integration, not the core backend
- [x] Start with one primary customer-facing assistant
- [x] Enforce multi-tenancy at database and API levels
- [x] Dashboard-first operations experience is the main sales differentiator

## 20. Change Tracking

Update this table whenever a major architecture milestone is completed.

| Date | Area | Change | Owner | Notes |
|---|---|---|---|---|
| 2026-04-24 | Planning | Initial production architecture plan created | Codex | Baseline document for execution tracking |
| 2026-04-24 | Planning | Multitenant model, role matrix direction, and order lifecycle decisions expanded | Codex | Phase 0 architecture decisions documented |
| 2026-04-24 | Planning | Public/admin API boundary and first-pass migration strategy documented | Codex | Architecture moved from vision into implementation planning |
| 2026-04-25 | Backend | Public/admin API cutover started with normalized order writes, admin order endpoints, status transition validation, and customer tracking | Codex | Legacy routes kept for compatibility while `/public`, `/admin`, and `/webhooks` routes are introduced |
| 2026-04-25 | Frontend | Menu and checkout switched to public API routes and success flow now shows order number and tracking code | Codex | Frontend remains customer-facing only; admin dashboard UI is still pending |
| 2026-04-25 | Frontend | First admin dashboard shipped with live queue, filters, order detail, status actions, cancellation controls, and summary cards | Codex | Implemented at `/admin/orders`; auth hardening is still pending |
| 2026-04-25 | Testing | Added backend unit coverage for public menu, order creation, admin order operations, transition validation, and tracking timeline | Codex | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest backend/tests/test_order_api.py -vv -s` passes in the current environment |
