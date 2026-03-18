# WhatsApp Food Ordering System
**By Veloxa Technology Ltd**

A production-ready WhatsApp food ordering system for Ghanaian restaurants.
Customers browse a mobile-first menu web app, build a cart, and order via WhatsApp.
The restaurant owner receives order details on their WhatsApp instantly.

---

## Architecture

```
Customer Phone
    ↓
Menu Web App (Next.js → Vercel)
    ↓ "Order on WhatsApp" button
WhatsApp (pre-filled order message)
    ↓
FastAPI Backend (Render)
    ↓
Supabase (PostgreSQL)
    ↓
Owner WhatsApp Notification (Meta Cloud API)
```

---

## Stack

| Layer | Tech | Hosting |
|---|---|---|
| Menu Web App | Next.js 14 + Tailwind | Vercel (free) |
| Backend API | FastAPI (Python) | Render (free) |
| Database | Supabase (PostgreSQL) | Supabase (free) |
| WhatsApp | Meta Cloud API | Free (1000 conv/mo) |
| Images | Supabase Storage | Supabase (free) |

---

## Project Structure

```
whatsapp-food-ordering/
├── menu-app/          # Next.js frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── styles/
│   ├── package.json
│   └── next.config.js
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── requirements.txt
│   └── .env.example
└── docs/
    └── SETUP.md
```

---

## Quick Start

### 1. Menu Web App
```bash
cd menu-app
npm install
cp .env.example .env.local
npm run dev
```

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

---

## Environment Variables

### menu-app/.env.local
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_RESTAURANT_WHATSAPP=233XXXXXXXXX
```

### backend/.env
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
META_ACCESS_TOKEN=your_meta_access_token
META_PHONE_NUMBER_ID=your_phone_number_id
OWNER_WHATSAPP=233XXXXXXXXX
```

---

## Deployment

- **Menu App**: Push to GitHub → connect to Vercel → auto-deploy
- **Backend**: Push to GitHub → connect to Render → set env vars → deploy

---

## Business Model

- Free for 1 month (trial)
- GHS 400–600/month after trial
- Setup fee: GHS 200 (optional)
