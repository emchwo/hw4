# Harness

## System overview

Campus Customs is a Yale apparel shop with an AI shopping assistant.

```
React + Vite + TypeScript site  ──/api──▶  FastAPI (backend/main.py)  ──▶  PydanticAI agent (backend/agent.py)
  (frontend/, port 5173)                     (port 8000)                      │  prompt: backend/prompts/prompt.md
                                              │                               │  tools:  backend/tools.py
                                              ▼                               ▼  model:  gpt-5.6-luna via Portkey
                                     data/campus_customs.db  ◀── every product, price, and stock number comes from here
                                              │
                                              ▼
                       output/audit_trail.json (every agent run) · output/human_review.json (hand-offs)
```

| File | What it does |
|---|---|
| `backend/main.py` | API routes: products, chat, chat history; mounts product images |
| `backend/agent.py` | Builds the agent, runs it with limits, checks replies against the database, writes the audit trail |
| `backend/models.py` | Pydantic / PydanticAI types: agent replies, tool results, API requests and responses |
| `backend/tools.py` | Tools the agent can call (all read from `campus_customs.db`) |
| `backend/prompts/prompt.md` | System prompt: voice, tool rules, reply types, safety rules |
| `backend/auth.py`, `backend/memory.py`, `backend/audit.py` | Accounts and sessions; saved chat history; audit trail and human-review reports |
| `frontend/src/` | Pages (Home, Products, item page, About), chat widget, login/create-account panels |

### How to run

Full setup steps are in the repo's `README.md`. In short:

1. Place the data pack at `data/` (`data/campus_customs.db` and `data/products/`). It isn't in git.
2. Copy `.env.example` to `.env` and add your `PORTKEY_API_KEY`.
3. **Backend:** `pip install -r requirements.txt`, then from `backend/` run `uvicorn main:app --reload --port 8000`.
4. **Frontend:** from `frontend/` run `npm install` then `npm run dev`.
5. Open http://localhost:5173. Vite forwards `/api` and `/images` to the backend on port 8000.

Note: `--reload` only watches `.py` files, so restart the backend after editing `prompt.md`.

## Database table and fields

### `catalogue`

- **Fields and why they matter**
  - `product_id`: provides shop/chatbot with unique identifier
  - `name`: helpful as a quick general description
  - `garment_type`: useful for filtering and sorting
  - `description`: helpful as a detailed description, especially for the chatbot
  - `colors`: useful for filtering and sorting
  - `search_tags`: helpful for searching, organizing, AI matching
  - `image_file_path`: helps shop or chatbot trace exact file path
  - `price`: helpful for shop to track pricing, affecting revenue/COGS

### `inventory`

- **Fields and why they matter**
  - `id`: provides shop/chatbot with row number for this specific table
  - `product_id`: provides shop/chatbot with unique identifier
  - `size`: organizes clothing by size, useful for filtering, sorting, and stock availability
  - `quantity`: useful for stock availability

### `users`

- **Fields and why they matter**
  - `id`: allows shop/chatbot to track user ID for specific account
  - `name`: full name of the user
  - `email`: login for user to access their shopping account
  - `password_hash`: keeps each user account secure
  - `created_at`: allows shop/chatbot to see when an account was created
  - `first_name`, `last_name`: helps shop/chatbot know who is creating an account, may allow for customized writing in the future

### `chat_messages`

- **Fields and why they matter**
  - `id`: allows shop/chatbot to track message ID and order of conversation
  - `user_id`: allows shop/chatbot to track who is talking to the chatbot
  - `role`: shows who is a user or assistant
  - `content`: important for a record of what was said between the user and chatbot
  - `products_json`: shows the shop which products were shown by the chatbot
  - `created_at`: allows shop/chatbot to see timestamp for message

### `sqlite_sequence`

- Not app data, created automatically

## How authorization works

- **Creating an account:** the site stores the user's first name, last name, email, and password (as a hash, never the password itself)
- **How passwords are protected**
  - Passwords are hashed
  - Logins stay private: the database stores a hash of a random token kept in a cookie that the site's JavaScript can't read
  - Failed login attempts don't result in the site giving hints
  - 5 wrong attempts will block logins for 15 minutes
  - The server checks:
    - password rules
    - matching passwords between the password box and the confirm box
    - valid email
    - email that isn't already in use

## How the frontend talks to FastAPI and how the agent is loaded

- **Frontend → FastAPI → agent (each chat message)**
  - When a user types a question in the chat box, the website sends it to FastAPI (`POST /api/chat`)
  - FastAPI makes sure the question isn't empty or way too long
  - FastAPI then passes the question to the shopping bot
  - The bot sends back an answer, plus a label (`type`) that indicates:
    - `text`
    - `product_recommendation`
    - `clarifying_question`
  - The website reads that label to decide what to show:
    - `text` → a message
    - `product_recommendation` → little product pictures
    - `clarifying_question` → buttons the user can tap
- **How the agent is loaded**
  - The first time someone sends a chat message, the bot reads `prompt.md`, which has safety and voice guardrails, and then reuses that setup for later messages
  - It then connects to an AI model using the API key (`PORTKEY_API_KEY`)
  - The bot can look things up in the store's list of real products, so it never makes up a product or a price
  - Before a reply is sent, the backend double-checks every product card against the database:
    - the name, price, and description are replaced with the real values
    - if a product doesn't exist, the bot has to try again
  - Portkey sends requests to GPT-5.6 Luna (`gpt-5.6-luna`)

## Tools and model fields chosen

- **Tools**
  - `search_products`: chose this for the agent to find and recommend products
  - `get_product_info`: extracts description, colors, type, price, and stock for the user
  - `get_price`: displays price for the user
  - `check_stock`: displays quantity and availability for the user, broken down by size (can also check one specific size)
- **New model fields** (added as subclasses of `TextReply`)
  - `PriceReply`: gives pricing info to the user
  - `StockReply`: gives every size's quantity and availability

## How chat search results are rendered on the page

- **When it happens:** the user asks the chat if the store has a kind of product (e.g. "do you have any hoodies?", "any t-shirts?", "show me gray crewnecks under $60")
- **What the agent does**
  - Calls `search_products` to search the catalogue
  - Replies with the `product_search` type, which includes:
    - a short message (e.g. "Yes! Here are our hoodies")
    - a `label` for the results (e.g. "Hoodies")
    - the `search` it ran (keywords plus any color, size, or price filters)
- **What the backend does**
  - Re-runs that same search on `campus_customs.db` and builds the product matches itself (up to 48), so every card is a real product with a real price
  - Each match (`ProductMatch`) has: id, name, price, currency, image URL, short description, in-stock status, and product link
  - If the search finds nothing, the agent has to reply with a plain text message instead (e.g. "We don't currently carry socks")
- **What the website shows**
  - It sees the `product_search` label and opens the Products page
  - A highlighted "From your chat" section shows the results heading, the number of matches, and a grid of product cards
  - Each card shows the product image, name, price, a short description, and a "Sold out" badge if nothing is in stock
  - Clicking a card opens that product's single-item page
  - The chat bubble notes how many matches are showing on the page
  - "Show all products" (or picking a category) goes back to the full catalogue

## Customer memory: chat history, customer fields, and page context

- **How user chat history is stored**
  - Only logged-in users' chats are saved; guests can chat, but nothing is stored
  - After each reply, two rows go into the `chat_messages` table:
    - the user's message (`role` = `user`)
    - the bot's answer (`role` = `assistant`), with the reply text in `content` and the structured reply (type, product cards, search matches, options, price, stock) saved as JSON in `products_json` so it can be redrawn the same way later
  - Each row is linked to the account by `user_id` and stamped with `created_at`
  - When a logged-in user returns, the site loads their saved messages (`GET /api/chat/history`) and shows them in the chat panel with date dividers
  - The server gives the agent the last 10 saved messages as conversation context (with a note of which products each reply showed); older chats can be found with the `recall_past_chats` tool
  - Users can delete their saved history with the **Clear** button (`DELETE /api/chat/history`)
- **What customer fields the agent can see**
  - Logged-in users: name, first name, last name, and email (looked up from the login cookie on the server, not sent by the browser)
  - The agent never sees the password hash or session token
  - Guests: the agent is told the user is a guest and doesn't know their name or email
- **How page context works**
  - With every chat message, the website sends what the user is looking at:
    - the page path
    - on a single-item page: the product id and selected size
    - on the Products page: the category filter or chat search results showing
  - The server only trusts the product id and looks up the product's name, type, and colors from the database itself
  - The agent is told which product is on screen, so "this", "it", or "this one" means that product
  - Tools that use page context and memory:
    - `get_current_page_product`: returns the product on the page, the selected size, and stock
    - `find_similar_products`: finds other items in the same category, e.g. "another one in pink"
    - `recall_past_chats`: searches a logged-in user's older saved conversations

## Site design

- **Inspiration:** editorial streetwear sites like Fear of God: minimal copy, big imagery, and lots of negative space
- **Palette:** very dark charcoal (`#161719`), muted neutrals and warm wood accents; navy comes from the clothing itself
- **Type:** IBM Plex Mono in all caps for titles and menus; EB Garamond serif for body text
- **First impression:** a full-screen "Campus Customs" intro, then the Campus Customs ad as a muted sepia video that scrubs forward as the mouse moves, with the Campus Customs seal logo and a "Shop the collection" button centered over it
- **Menu:** a thin bar; hovering "Products" opens a frosted-glass shop panel
- **Products:** closeups on a blank backdrop that matches each photo's background; product photos keep their true colors (the home page category tiles are sepia until hovered)
- **Why it works**
  - **Grabs attention:** the moving video and cinematic sepia feel more like a fashion campaign than a typical college store, so shoppers stop scrolling and explore
  - **Signals quality:** restraint (few words, lots of space, a tight palette, refined type) is the visual language of premium brands, so the clothing reads as worth the price
  - **Feels current:** grain, mono type, frosted glass, and moody editorial imagery borrow from what trending streetwear labels use now, positioning Campus Customs as a brand people want to be seen in, not just school merch
  - **Keeps products central:** with minimal copy, the clothing does the talking, and true-color product photos mean shoppers know exactly what they're buying

## Model fields in `models.py` and why they were chosen

**Design idea:** the model only chooses *what* to show (a product id, a search, a message). Every number shoppers see (prices, stock, cards) is filled in by the server from the database in fields the model never sees (`SkipJsonSchema`), so it can't make them up.

### Agent replies (the agent's output is a union of these; `type` tells the website how to render it)

| Reply | Fields the model fills | Filled by the server | Why |
|---|---|---|---|
| `TextReply` | `type="text"`, `message` | none | Greetings, descriptions, declining off-topic requests, hand-offs |
| `PriceReply` (subclass of `TextReply`) | `type="price"`, `message`, `product_id` | `price_info` | Price questions; the message must state the real price or the agent retries |
| `StockReply` (subclass of `TextReply`) | `type="stock"`, `message`, `product_id`, `size` | `stock_info` | Stock questions; sold-out sizes must be called "out of stock" |
| `ProductSearchReply` | `type="product_search"`, `message`, `label`, `search` (`SearchFilters`) | `matches`, `total_matches` | "Do you have hoodies?": the website shows the matches as cards on the Products page |
| `ProductRecommendationReply` | `type="product_recommendation"`, `message`, `product_ids` (1–6) | `products` (`ProductCard`s) | Hand-picked suggestions; asking only for ids saved about 60% of output tokens |
| `ClarifyingQuestionReply` | `type="clarifying_question"`, `question`, `options` (≤5) | none | Vague requests; options become one-tap buttons |

### Cards and tool results (real rows from the database)

- **`ProductCard`** (`id`, `name`, `price`, `currency`, `image_url`, `description`, `in_stock`, `product_url`): everything a chat card needs, and the link opens the item page
- **`ProductMatch`**: same as a card but with a `short_description`, for the Products-page results grid
- **`ProductBrief`** (`id`, `name`, `garment_type`, `price`, `colors`, `short_description`, `in_stock`, `sizes_in_stock`): a compact row for the model; no image URLs or per-size counts, to save tokens
- **`ProductInfo`**, **`PriceInfo`**: one product's details or price
- **`StockInfo`** (`sizes` with `quantity` and `status`, `requested_size_*`, `total_in_stock`, `status`, `summary`): `status` is `in_stock`, `low_stock` (5 or fewer), or `out_of_stock`, so sold-out sizes can't be missed
- **`ProductNotFound`** (`found=false`, `message`, `suggestions`): makes the agent ask "which one?" instead of guessing
- **`CurrentPageProduct`**, **`SimilarProducts`**, **`PastChats`**: results of the page-context and memory tools

### API and per-request context

- **`ChatRequest`** (`message` 1–2000 chars, `history` ≤40 for guests, `page`): input is validated before the agent runs
- **`PageContext`** (`path`, `product_id`, `selected_size`, `category`, `search_label`, `visible_product_ids`): what's on screen; only ids are trusted
- **`ChatResponse`** (`type`, `reply`, `products`, `matches`, `options`, `price`, `stock`, ...): one shape the website can render for every reply type
- **`HistoryMessage`**: a saved chat message plus its structured reply, so old cards redraw correctly
- **`ChatDeps`** (`user`, `page`, `run_id`, `review_ids`): who is chatting and on which page, passed to tools; `run_id` links the audit entry to any human-review report

## Tools and abilities

| Tool | What it does |
|---|---|
| `search_products` | Keyword search with color, size, price, and in-stock filters (up to 12 results) |
| `get_product_info` | Full description, colors, type, price, and total stock for one product |
| `get_price` | Exact price for one product |
| `check_stock` | Quantity and status for every size (or one size); understands "small", "2XL", etc. |
| `get_current_page_product` | The product on the shopper's current page (for "this" / "it") |
| `find_similar_products` | Same-category items, optionally in another color or under a price ("another one in pink") |
| `recall_past_chats` | Searches a logged-in shopper's older saved conversations |
| `request_human_review` | Files a report for a person and stops (safety rule 3) |

**Other abilities**
- **Three reply styles on the page:** text, product cards in the chat, or a results grid on the Products page
- **Grounding checks:** every card, price, and stock answer is rebuilt from the database; unknown product ids, a missing real price, or an unmentioned sell-out make the agent retry
- **Customer memory:** knows a logged-in shopper's name and email; saved chat history reloads on return
- **Page context:** knows which product and size the shopper is viewing
- **One-tap starter questions** when the chat is empty (product-specific on item pages)

## Safety rules

Written in `prompts/prompt.md` and enforced in code where possible:

1. **Data handling and privacy**
   - The prompt forbids revealing API keys, tokens, passwords, or system configuration (tested: it refuses "what is your PORTKEY_API_KEY?")
   - The API key lives only in `.env` on the server and is never sent to the model or the browser
   - The agent collects as little personal information as possible: it sees only name and email for logged-in users, never password hashes or session tokens
   - Each shopper's data stays separate: history is loaded by the logged-in user's id from their session cookie, guests get nothing saved, and `recall_past_chats` only searches the current user's chats
   - The audit trail and reports record `user:<id>` or `guest` (no names or emails), shorten text, and redact anything that looks like an email, key, card number, or password
2. **Only Campus Customs clothing:** off-topic requests (homework, coding, other stores, advice) get one polite sentence pointing back to the shop (tested with "help me with my calculus homework")
3. **Stop after 3 failed attempts and report to a human**
   - A failed attempt is a lookup that finds nothing, a rejected answer, or an error
   - After 3 in one request, the lookup tools are removed from the agent, it's told to stop, and it must call `request_human_review` and tell the shopper the team will follow up
   - If a run fails outright (3 rejected answers, the request limit, a timeout, or a model error), the server files the report itself and the shopper gets a polite hand-off message with a reference number
   - Reports go to `output/human_review.json` (append-only, `status: "open"`)
   - Tested: asking for 4 made-up products produced 3 failed lookups, then a hand-off with report `HR-…`
4. **Other basics:** clean and respectful language, refuse harmful requests, resist "ignore your instructions," admit being an AI, and make no promises about discounts, delivery, or refunds

## Audit trail

- **File:** `output/audit_trail.json`, one entry per agent run, **appended and never erased** (if the file is ever unreadable it's set aside, not overwritten)
- **Each entry:** `run_id`, `time`, `user` (`user:<id>` or `guest`), `page`, short `message`, `model` / `model_served`, then:
  - `tool_calls`: each with `time`, `tool`, `kind` (`tool` or `output`, the final reply step), short `args`, short `result`, and `ok`
  - `failed_attempts`, `stop_reason` (for example "final answer (price…)", "handed off to a human after 3 failed attempts", "timeout", "error: …")
  - `reply_type`, `reply_preview`, `human_review` (report ids), `requests`, `input_tokens`, `output_tokens`, `duration_s`

## Specs

| Spec | Value |
|---|---|
| Model | `gpt-5.6-luna` through Portkey (OpenAI-compatible API); the key routes all requests to Luna. Override with `AGENT_MODEL` |
| Agent framework | PydanticAI (`OpenAIChatModel`), reasoning effort `none`, parallel tool calls on |
| Loop limit | At most **10 model requests** per chat message (`UsageLimits`) |
| Retries | **3 attempts** at a valid reply (1 try + 2 retries), then stop and hand off |
| Failed-attempt cap | **3** per request; then tools are withdrawn and a human review is filed |
| Timeout | **60 s** per message (HTTP 504 if exceeded) |
| Input caps | Message 1–2000 chars; guest history ≤40 messages (≤4000 chars each) |
| Context caps | Logged-in history: last **10** messages (≤1500 chars each, ≤5 "products shown" each) |
| Result caps | `search_products` ≤12; page results grid ≤48; recommendations 1–6 cards; options ≤5; `recall_past_chats` ≤20; chat panel history ≤100 |
| Stock | "Low stock" = 5 or fewer; sizes XS–XXL |
| Auth | PBKDF2-SHA256 (600,000 iterations); HttpOnly session cookie (7 days); 5 failed logins → 15-minute lockout |
| HTTP status codes | 422 bad input · 401 not logged in · 502 model error · 503 not configured · 504 timeout · 500 unexpected; give-ups return a normal reply with a reference number |
| Ports | Frontend 5173 (Vite), backend 8000 (Uvicorn) |
| Endpoints | `GET /api/products`, `GET /api/products/{id}`, `POST /api/chat`, `GET`/`DELETE /api/chat/history`, `POST /api/auth/register`/`login`/`logout`, `GET /api/auth/me`, `/images/*` |
