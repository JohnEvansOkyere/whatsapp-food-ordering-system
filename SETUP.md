# Setup Guide — WhatsApp Food Ordering System
**From zero to live in a day**

---

## Step 1: Supabase (Database)

1. Go to https://supabase.com → Create account → New project
2. Pick a name, set a strong password, choose nearest region (Frankfurt for Ghana)
3. Once created, go to **SQL Editor** → paste contents of `backend/supabase_schema.sql` → Run
4. Go to **Settings → API** → copy:
   - `Project URL` → this is your `SUPABASE_URL`
   - `anon public` key → this is your `SUPABASE_KEY`

---

## Step 2: Meta WhatsApp Cloud API

1. Go to https://developers.facebook.com → Create App
2. Select **Business** app type
3. Add **WhatsApp** product to your app
4. Go to **WhatsApp → Getting Started**
5. You'll get a test phone number — use it for development
6. Copy:
   - `Access Token` → `META_ACCESS_TOKEN`
   - `Phone Number ID` → `META_PHONE_NUMBER_ID`
7. Set `META_VERIFY_TOKEN` to any random string you choose (e.g. `accra_eats_verify_2024`)
8. Add your personal WhatsApp number as a test recipient

**For production:** You'll need to submit the app for review and get a real business number. For the 1-month free trial, the test number is enough.

---

## Step 3: Deploy Backend to Render

1. Push your code to a GitHub repo
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo → select the `backend` folder as root
4. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add all environment variables from `backend/.env.example`
6. Set `ALLOWED_ORIGINS` to your Vercel URL (get this after Step 4)
7. Deploy → copy your Render URL (e.g. `https://your-api.onrender.com`)

---

## Step 4: Deploy Menu App to Vercel

1. Push `menu-app` folder to GitHub (can be same repo)
2. Go to https://vercel.com → New Project → Import repo
3. Set **Root Directory** to `menu-app`
4. Add environment variables:
   - `NEXT_PUBLIC_API_URL` = your Render URL
   - `NEXT_PUBLIC_RESTAURANT_WHATSAPP` = owner WhatsApp number (no + or spaces, e.g. `233244123456`)
   - `NEXT_PUBLIC_RESTAURANT_NAME` = restaurant name
5. Deploy → copy your Vercel URL

---

## Step 5: Connect WhatsApp Webhook

1. Back in Meta Developer Console → WhatsApp → Configuration
2. **Webhook URL:** `https://your-api.onrender.com/webhook/whatsapp`
3. **Verify Token:** same value you set in `META_VERIFY_TOKEN`
4. Click Verify and Save
5. Subscribe to `messages` webhook field

---

## Step 6: Update Menu URL in Webhook

In `backend/app/routers/webhook.py`, find this line:
```python
menu_url = "https://your-menu-app.vercel.app"
```
Replace with your actual Vercel URL.

Redeploy the backend.

---

## Step 7: Test End to End

1. Open your Vercel menu URL on your phone
2. Add items to cart
3. Tap "Order on WhatsApp" — it should open WhatsApp with a pre-filled message
4. Send the message to the WhatsApp test number
5. The bot should respond with the menu link
6. Complete the order flow
7. Check that the owner WhatsApp number received the order notification

---

## Customising for a Real Restaurant

### Change restaurant details:
Edit `menu-app/src/lib/menuData.ts`:
- Update `RESTAURANT` object with real name, address, hours, WhatsApp
- Replace `MENU_ITEMS` with their actual menu
- Replace Unsplash image URLs with real food photos (upload to Supabase Storage)

### Change branding colors:
Edit `menu-app/tailwind.config.js` → update the `brand` color values

---

## Cost Breakdown (Free Tier)

| Service | Free Tier Limit | Notes |
|---|---|---|
| Supabase | 500MB DB, 1GB storage | Enough for hundreds of restaurants |
| Vercel | 100GB bandwidth/month | More than enough |
| Render | 750 hours/month (sleeps after 15min inactivity) | Upgrade to $7/mo for first client |
| Meta WhatsApp | 1,000 conversations/month | Enough for MVP |

**Total monthly cost for MVP: $0**
**After first paying client: ~$7–25/month max**

---

## When You Get Your First Client

1. Fork/copy this codebase → rename for their restaurant
2. Update `menuData.ts` with their menu
3. Get their food photos (ask them, or photograph yourself)
4. Deploy fresh Vercel + Render instances for them
5. Connect their WhatsApp Business number
6. Done — charge GHS 400–600/month
