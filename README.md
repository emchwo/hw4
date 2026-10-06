# Campus Customs

A Yale apparel shop with an AI shopping assistant. The **frontend** is React + Vite + TypeScript, the **backend** is FastAPI, and the **agent** is PydanticAI calling `gpt-5.6-luna` through Portkey. Every product, price, and stock number comes from a SQLite database, so the agent can't make them up.

## Repo layout

```
hw4/
├── AI_prompts.md            # prompts used for each problem
├── requirements.txt         # backend Python dependencies
├── .env.example             # copy to .env and add your key
├── .gitignore
├── README.md
├── frontend/                # Vite React TypeScript app
├── backend/
│   ├── main.py              # FastAPI app — run with: uvicorn main:app --reload
│   ├── agent.py             # ┐
│   ├── models.py            # │ the agent (4 files)
│   ├── tools.py             # │
│   ├── prompts/prompt.md    # ┘
│   ├── auth.py              # accounts and login sessions
│   ├── memory.py            # saved chat history
│   ├── audit.py             # audit trail and human-review reports
│   ├── db.py                # database path and connection
│   └── set_password.py      # helper: reset a user's password
└── output/
    ├── harness.md           # how the whole system works
    ├── design.md            # site design
    ├── usability.md         # usability improvements
    ├── app_check.html       # test report (screenshots in app_check_images/)
    ├── audit_trail.json     # agent-loop log (appended, never erased)
    └── human_review.json    # hand-offs after 3 failed attempts
```

## Data pack (not in git)

The database and product photos are kept out of the repo. Place them at `data/` in the repo root:

```
hw4/
└── data/
    ├── campus_customs.db
    └── products/            # images referenced by the catalogue
```

## Setup

You need **Python 3.11+**, **Node.js 18+**, and a **Portkey API key**.

### 1. Add your key

Copy `.env.example` to `.env` and set `PORTKEY_API_KEY`:

```bash
cp .env.example .env
```

### 2. Run the backend (port 8000)

From the repo root, create a virtual environment and install dependencies:

```bash
python -m venv .venv
```

Activate it (Windows):

```bash
.venv\Scripts\activate
```

Or on macOS/Linux:

```bash
source .venv/bin/activate
```

Then install and start the API from `backend/`:

```bash
pip install -r requirements.txt
```

```bash
cd backend
```

```bash
uvicorn main:app --reload --port 8000
```

Check it's up: http://localhost:8000/api/health should return `{"status": "ok"}`.

### 3. Run the frontend (port 5173)

In a second terminal, from the repo root:

```bash
cd frontend
```

```bash
npm install
```

```bash
npm run dev
```

Open **http://localhost:5173**. Vite forwards `/api` and `/images` to the backend on port 8000, so both servers must be running.

## Using the site

- **Shop:** browse Products, filter by category, open any item for price, colors, and stock by size.
- **Chat:** the button in the bottom right opens the assistant. Try a starter question, or ask things like "do you have any hoodies?", "how many mediums of the Baseball Left Chest Crewneck are left?", or, on an item page, "do you have this in gray?".
- **Accounts:** use **Create Account** to make a login. Logged-in shoppers' chats are saved and reload when they return.
  - **Test login:** `test@campuscustoms.yale.edu` / `password`. The original data pack stores this account's password in an older format, so the backend re-saves it in the current format the first time it starts.
  - The other seed accounts keep the older format and can't log in. To set a password for one, run this from `backend/` (it prompts for the new password):
    ```bash
    python -m set_password ada.1789818990@yale.edu
    ```

## Notes

- The backend creates a `sessions` table in the database on first start (for login sessions).
- `--reload` only watches `.py` files, so restart the backend after editing `prompts/prompt.md`.
- The agent's activity is appended to `output/audit_trail.json`; hand-offs to a person go to `output/human_review.json`.
- See `output/harness.md` for the full system description: model fields, tools, safety rules, limits, and endpoints.
