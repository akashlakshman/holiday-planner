# Holiday Planner ✈

An AI-powered holiday itinerary generator with live flight and hotel search.

## Features

- **AI Itinerary Generation** — supports Google Gemini, Anthropic Claude, and OpenAI GPT-4o
- **Live Flights** — real flight offers via Amadeus API (sandbox or production)
- **Live Hotels** — real hotel options via Amadeus Hotel Search
- **Save & Retrieve** — persist itineraries to Supabase
- **5-step questionnaire** — purpose, style, travellers, interests, dietary requirements
- **Responsive UI** — clean single-page frontend, no framework required

## Structure

```
holiday-planner/
├── backend/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Settings (pydantic-settings + .env)
│   ├── models.py            # Pydantic request/response models
│   ├── requirements.txt
│   ├── .env.example
│   ├── routers/
│   │   ├── itinerary.py     # POST /api/itinerary/generate, /save, GET /{id}
│   │   ├── flights.py       # POST /api/flights/search, GET /api/flights/iata
│   │   └── hotels.py        # POST /api/hotels/search
│   └── services/
│       ├── ai_service.py    # Gemini / Claude / GPT-4o itinerary generation
│       ├── amadeus_service.py  # Amadeus flight + hotel search
│       └── supabase_service.py # Persistence
└── frontend/
    ├── pages/index.html     # Main planner page
    ├── styles/styles.css
    └── scripts/app.js
```

## Setup

### 1. Backend

```bash
# Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Copy and fill in your keys
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# Run the API server
python3 -m uvicorn backend.main:app --reload --port 8000
```

### 2. Frontend

Open `frontend/pages/index.html` directly in a browser, or serve with any static file server:

```bash
# e.g. using Python's built-in server from the frontend directory
cd frontend
python3 -m http.server 3000
# then open http://localhost:3000/pages/index.html
```

### 3. Environment Variables

Copy [`backend/.env.example`](backend/.env.example) to `backend/.env` and fill in your keys:

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key |
| `ANTHROPIC_API_KEY` | Anthropic Console API key |
| `OPENAI_API_KEY` | OpenAI Platform API key |
| `AMADEUS_CLIENT_ID` | Amadeus for Developers client ID |
| `AMADEUS_CLIENT_SECRET` | Amadeus for Developers client secret |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon/public key |

> At least one AI provider key is required. Amadeus and Supabase are optional — the app degrades gracefully without them.

### 4. Supabase Table (optional)

If you want to save itineraries, create this table in your Supabase project:

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

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check & provider status |
| `POST` | `/api/itinerary/generate` | Generate AI itinerary |
| `POST` | `/api/itinerary/save` | Save itinerary to Supabase |
| `GET` | `/api/itinerary/` | List saved itineraries |
| `GET` | `/api/itinerary/{id}` | Retrieve saved itinerary |
| `POST` | `/api/flights/search` | Search flight offers |
| `GET` | `/api/flights/iata?city=London` | Resolve city to IATA code |
| `POST` | `/api/hotels/search` | Search hotel offers |

Interactive API docs available at `http://localhost:8000/docs` when the server is running.
