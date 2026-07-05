# Holiday Planner ✈

An AI-powered holiday itinerary generator with live hotel search and flight booking links.

## Features

- **AI Itinerary Generation** — day-by-day personalised plans via Google Gemini 2.5 Flash, Anthropic Claude, or OpenAI GPT-4o
- **Live Hotel Search** — real Booking.com results with direct booking links (via RapidAPI)
- **Flight Search Links** — pre-filled Skyscanner and Google Flights links for your exact route, dates and passenger count
- **5-step questionnaire** — trip purpose, style, travellers, interests, dietary requirements
- **Form persistence** — all form fields saved to `localStorage`, restored on refresh
- **Save & Retrieve** — optionally persist itineraries to Supabase
- **Responsive UI** — clean single-page vanilla HTML/CSS/JS frontend, no framework needed

## Project Structure

```
holiday-planner/
├── backend/
│   ├── main.py                        # FastAPI app, CORS, router mounts
│   ├── config.py                      # Settings loaded from .env
│   ├── models.py                      # Pydantic request models
│   ├── requirements.txt
│   ├── .env.example
│   ├── prompts/
│   │   └── itinerary_prompt.py        # AI prompt builder
│   ├── routers/
│   │   ├── itinerary.py               # POST /api/itinerary/generate|save, GET /api/itinerary/
│   │   ├── flights.py                 # POST /api/flights/search (returns deep links)
│   │   └── hotels.py                  # POST /api/hotels/search (live Booking.com)
│   └── services/
│       ├── ai_service.py              # Gemini / Claude / GPT-4o dispatch + retry
│       ├── rapidapi_service.py        # Booking.com hotels + flight deep link builder
│       └── supabase_service.py        # Optional persistence
└── frontend/
    ├── pages/index.html               # Main planner page
    ├── styles/styles.css
    └── scripts/app.js                 # Form logic, API calls, result rendering
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` — you only need **one AI key** to get started:

| Variable | Required | Where to get it |
|---|---|---|
| `GEMINI_API_KEY` | ✅ At least one AI key | [aistudio.google.com](https://aistudio.google.com/app/apikey) — free |
| `ANTHROPIC_API_KEY` | Optional | [console.anthropic.com](https://console.anthropic.com) |
| `OPENAI_API_KEY` | Optional | [platform.openai.com](https://platform.openai.com) |
| `RAPIDAPI_KEY` | Optional (hotels) | [rapidapi.com](https://rapidapi.com) — subscribe to **Booking.com by apidojo** (free tier) |
| `SUPABASE_URL` + `SUPABASE_ANON_KEY` | Optional (save trips) | [supabase.com](https://supabase.com) — free tier |

### 3. Run the backend

```bash
python3 -m uvicorn backend.main:app --reload --port 8000
```

### 4. Open the frontend

Open `frontend/pages/index.html` directly in your browser, or serve it:

```bash
cd frontend && python3 -m http.server 3000
# then open http://localhost:3000/pages/index.html
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check + configured provider status |
| `POST` | `/api/itinerary/generate` | Generate AI itinerary (`TripRequest` body) |
| `POST` | `/api/itinerary/save` | Save itinerary to Supabase |
| `GET` | `/api/itinerary/` | List saved itineraries |
| `GET` | `/api/itinerary/{id}` | Retrieve saved itinerary |
| `POST` | `/api/flights/search` | Returns Skyscanner + Google Flights deep links |
| `POST` | `/api/hotels/search` | Live hotel search via Booking.com |

Interactive docs at `http://localhost:8000/docs` when server is running.

## Supabase Setup (optional)

To enable saving itineraries, create this table in your Supabase project:

```sql
create table itineraries (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz default now(),
  trip_request jsonb,
  itinerary jsonb,
  flights jsonb,
  hotels jsonb
);
```

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.9+, FastAPI, Uvicorn |
| AI | Google Gemini 2.5 Flash (default), Claude 3.5 Sonnet, GPT-4o |
| Hotels | Booking.com via RapidAPI (apidojo) |
| Flights | Skyscanner + Google Flights deep links |
| Persistence | Supabase (optional) |
| Frontend | Vanilla HTML/CSS/JS — no framework |

## Notes

- **Flights**: Live flight pricing APIs have very low free-tier limits. The app instead generates pre-filled search links for Skyscanner and Google Flights — these open with your exact route, dates and passenger count already filled in.
- **Hotels**: Requires a RapidAPI key with the free **Booking.com by apidojo** subscription. Returns 3–5 results with direct Booking.com booking links.
- **AI retries**: On Gemini 503 (high demand), the service automatically retries up to 3 times with backoff before failing.
