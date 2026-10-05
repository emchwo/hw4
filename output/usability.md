# Usability improvements

Four improvements: two on the website (easier to use) and two on the agent/backend (cheaper and faster). For each: what was added, and why it helps a Campus Customs shopper or the business.

---

## Frontend

### 1. "Ask about this item" button + one-tap starter questions

**What was added**
- Every single-item page has an **💬 Ask about this item** button under the price. It opens the chat, and the agent already knows which product (and selected size) the shopper is looking at.
- When the chat is empty (just the greeting), it shows **one-tap starter questions**:
  - On a product page: "How much is this?", "Which sizes are in stock?", "Do you have this in another color?", "Show me similar items"
  - Elsewhere: "Do you have any hoodies?", "Gift ideas under $60", "What's in stock in size M?", "Show me quarter-zips"
- Files: `frontend/src/pages/ProductPage.tsx`, `frontend/src/components/ChatWidget.tsx`, `frontend/src/chatSearch.tsx`

**Why it helps**
- **Shopper:** many people don't notice a chat bubble or don't know what to ask. The button sits right where they're deciding (next to the price), and the starters show what the assistant can do. One tap gets an answer, with no typing, which also helps on phones.
- **Business:** more shoppers get their size or stock question answered on the spot instead of leaving the page. That means fewer abandoned visits and more add-to-cart moments. The starters also steer people toward questions the agent answers well (price, stock, similar items).

### 2. Richer chat answers: stock grid, price card, and formatted text

**What was added**
- **Stock replies** show a small **size grid** under the message (XS–XXL), color-coded green (in stock), amber (5 or fewer left), and red ("Out"), with the size the shopper asked about outlined and the total in stock. Clicking it opens the product page.
- **Price replies** show a **mini price card** (product name and price) that links to the product page.
- **Chat bubbles render basic formatting:** **bold** text and bulleted or numbered lists display properly instead of showing raw `**` and `-` characters (older saved chats used these). It's built from React elements, not raw HTML, so model text can't inject anything into the page.
- Files: `frontend/src/components/ChatWidget.tsx`, `frontend/src/components/RichText.tsx`, `frontend/src/index.css`

**Why it helps**
- **Shopper:** availability is visible at a glance. "Out of stock in XS and XL" becomes impossible to miss, and they can see right away which other sizes work. Lists and bold text are easier to scan than a wall of text.
- **Business:** clear stock answers set the right expectations, so there are fewer disappointed customers and support questions about sold-out sizes. The cards link back to the product page, keeping shoppers moving toward a purchase.

---

## Agent / backend

Measured with a fixed set of 6 typical questions (hoodie search, a price, a stock check, "this in gray?" from a product page, a gift idea, and "what did we talk about last time?") run directly against the agent. The "after" numbers are from the first post-change run; a second identical run came back in 3.7s total because the Portkey gateway caches repeated identical requests.

| | Before | After | Change |
|---|---|---|---|
| Output tokens (total) | 1,669 | 664 | **−60%** |
| Input tokens (total) | 57,250 | 55,548 | −3% |
| Time for all 6 questions | 33.7 s | 29.4 s | **−13%** |
| Model calls | 13 | 13 | same |

### 3. Leaner tool outputs, reply format, and history

**What was added**
- **Recommendation replies only ask the model for product ids** (`product_ids`) instead of full product cards. The server already rebuilt every card from the database, so having the model write out names, prices, image URLs and descriptions was wasted output. Writing output tokens is the slowest and most expensive part of a model call.
- **Search tools return a compact product summary** (`ProductBrief`: id, name, type, price, colors, one-line description, in stock, sizes in stock) instead of every field. Image URLs, links and per-size counts are dropped because the model never needs them; cards and links are built by the server, and `check_stock` gives exact counts.
- **Shorter conversation history:** logged-in shoppers' last **10** saved messages are sent to the model instead of 20, with at most 5 "products shown" per message. Older chats are still reachable with `recall_past_chats`.
- Files: `backend/models.py`, `backend/tools.py`, `backend/agent.py`, `backend/memory.py`, `backend/prompts/prompt.md`

**Why it helps**
- **Shopper:** faster replies. The "do you have this in gray?" answer went from 849 output tokens to 177.
- **Business:** cheaper to run. Output tokens fell 60% across the test set, and output tokens usually cost several times more than input tokens. Accuracy is unchanged because every card is still built from the database.

### 4. Lowest reasoning setting + parallel tool calls

**What was added**
- The agent now runs with **`reasoning_effort` explicitly set to `none`** (configurable with the `AGENT_REASONING_EFFORT` environment variable) and **`parallel_tool_calls` turned on**, so the model can, for example, check price and stock in the same round trip.
- A short **"be efficient" rule in the prompt:** make the fewest tool calls needed, call independent tools together, and when the exact product name or id is known, call `get_price` / `check_stock` / `get_product_info` directly without searching first.
- Note: `low` was the plan, but on this endpoint GPT-5.6 Luna rejects any reasoning effort except `none` when tools are attached. So the setting now documents the lowest option and guards against a future default change, and the speed gain comes from fewer, combined tool round trips.
- Files: `backend/agent.py`, `backend/prompts/prompt.md`

**Why it helps**
- **Shopper:** quicker answers to simple questions like "how much is this?" or "is M in stock?", which are the most common chat questions in a shop.
- **Business:** every model round trip resends roughly 4,000 tokens of instructions and tool definitions, so avoiding unnecessary calls is the biggest lever on cost per conversation. Shopping lookups don't need deep reasoning, so the cheapest setting costs nothing in quality.
