# Provisional Launch Data

The values in this document keep development and demonstrations moving. They
are not confirmed restaurant facts and must be replaced before launch.

## Branches

| Field | Ashesi University | Abelemkpe |
|---|---|---|
| Code | `ASHESI` | `ABELEMKPE` |
| Address label | Ashesi University campus | Abelemkpe, Accra |
| Service area | Ashesi campus and nearby Berekuso | Abelemkpe and nearby Accra areas |
| Hours | Daily 10:00–22:00 | Daily 10:00–22:00 |
| Delivery fee | GHS 5 | GHS 8 |
| Minimum order | GHS 25 | GHS 25 |
| ETA range | 35–60 minutes | 35–60 minutes |

The interface labels these values as provisional. Backend operating-hours
enforcement remains disabled until the restaurant confirms the schedule.

## Provisional Staff Accounts

The backend exposes these development usernames:

- `owner`: access to both branches;
- `ashesi`: Ashesi University only;
- `abelemkpe`: Abelemkpe only.
- `ashesi-kitchen` and `abelemkpe-kitchen`: kitchen actions for one branch.
- `ashesi-dispatch` and `abelemkpe-dispatch`: dispatch actions for one branch.
- `support`: cancellation, delay and support actions across both branches.

All use the password configured in `STAFF_DEMO_PASSWORD`. The repository default
is for local development only. Set a unique password and a strong
`STAFF_AUTH_SECRET` in every shared environment.

## Menu Options

- Jollof Rice + Chicken and Fried Rice + Chicken: optional plantain and
  coleslaw extras.
- Pepperoni Pizza and BBQ Chicken Pizza: regular or large size, with optional
  extra cheese or chicken.

All option prices are recalculated by the backend. Replace them with the
approved product configuration before accepting real orders.

## External Items Still Required

- approved restaurant identity and logo;
- real branch contacts, coordinates, hours, zones and fees;
- approved Meta WhatsApp templates and production number;
- selected Mobile Money provider and live webhook credentials;
- final privacy, refund and cancellation policies.
