# HW 4 — AI Prompts

<!--
Section format:

## Problem N: Title

**Initial prompt:**
> ...

**Follow-up prompts:**
1. > ...

**What the initial prompt lacked:** One sentence.
-->

## Problem 1: Vibe coder prompts

**Initial prompt:**
> create AI_prompts.md and update it as i work with the different prompts. each section should have the problem number and title (which i will give), the prompt i used, and any follow up prompts under that. there should be a sentence on what was lacking in the initial prompt following any potential followup prompts

**Follow-up prompts:**
1. > @"C:\Users\emily\Downloads\data (2).zip" — unzip this file. use PORTKEY_API_KEY for any agent calls, using opus 5.5.

**What the initial prompt lacked:** It only set up the logging workflow and gave no project data, task, or model/API instructions, so the data files and the choice of Opus 5.5 via Portkey had to come in a follow-up.

## Problem 2: Analyze the database

**Initial prompt:**
> help me understand the fields of each table in data/campus_customs.db, starting with catalogue, inventory, and users, then the other ones

**Follow-up prompts:**
1. > create output/harness.md and start a new section titled "Database table and fields". then include this underneath. feel free to reorganize the formatting with indentations so that it's more organized
   >
   > _(followed by my notes on each table — catalogue, inventory, users, chat_messages, sqlite_sequence — listing every field and why it matters)_

**Note:** I split this problem into two parts: first understanding the tables and fields, then writing up my own notes on why each field matters.

## Problem 3: Build the Campus Customs website

**Initial prompt:**
> create a React + Vite + TypeScript front end for Campus Customs. use FastAPI in backend/main.py, and i will add more to it later
>
> create a navigation bar at the top of the page with links to these main pages: home, products, about us, log in, create account. you can base the wording for the home page and the about us page on the wording and vibe of yalebulldogblue.com, but do not copy the original text they use. write any wording in your own voice as an agent, keep it professional and user-friendly. on the product page, use the image paths from data/campus_customs.db to create  a page with product images. each product should open into a single-item page with the image on the left hand side, full product text on the right with the description, price, sizes, stock quantity. when you click on the image card on the products page, it should take you to that single-item page.
>
> add a chatbot interface in the bottom right of the site, it just needs to be able to call to the backend later on

**Follow-up prompts:**
_None yet._

**What the initial prompt lacked:** _TBD after any follow-ups._

## Problem 4: Create account and login

**Initial prompt:**
> build a create account and login flow, when a user clicks on create account, create a floating panel that asks them to fill out their first name, last name, email, password, and confirm password
>
> for the login, create a floating panel that asks the user to put in their email and password, and have an icon of the yale bulldog handsome dan on there
>
> new accounts should go into the users table in the database, and ensure that the passwords are stored securely so no human or AI hackers can access them.
>
> after you make this i will test it in the page

**Follow-up prompts:**
1. > _(screenshot: Email: test@campuscustoms.yale.edu, Password: password)_ fix the backend so that i can use this information to test the login functionality of the page

**What the initial prompt lacked:** It didn't give credentials for an existing test account (or say that existing accounts needed to keep working), so the seed users' older password-hash format wasn't supported until the follow-up.

2. > update output/harness.md with a section titled "How authorization works" and put this underneath:
   >
   > _(followed by my notes on how accounts are stored and how passwords are protected)_

**Note:** Follow-up 2 was me splitting this problem into two parts: first building and testing the login flow, then writing up my own notes on how authorization works.

## Problem 5: PydanticAI agent backend

**Initial prompt:**
> the shop chatbot is a pydanticAI agent behind fastAPI which is connected to the frontend chat. in backend/main.py which you already created earlier, put in these four files:
>
> * backend/prompts/prompt.md - system prompt, i will add more to this later
> * backend/agent.py - agent entry and wiring
> * backend/tools.py - tools that the agent can use
> * backend/models.py - pydantic / pydanticAI structured types
>
> in main.py, create a POST /api/chat endpoint that accepts a JSON body like { "message": "user's text" }, passes it to my AI agent, and returns the agent's reply as JSON (e.g. { "reply": "..." }). handle errors gracefully (bad input, agent failure, timeout) and return sensible HTTP status codes. use PORTKEY_API_KEY for agent calls.
>
> in prompts/prompt.md, add in voice and safety basics e.g. don't let it say bad words or inappropriate things. add in whatever else is standard for voice and safety basics.
>
> in models.py, define structured output types - i want three kinds of replies: a plain text reply, a product recommendation reply that includes a short message plus a list of product cards (each with id, name, price, currency, image url, description, in-stock status, and product link), and a clarifying question reply for when the agent needs more info. give the agent a type field on each reply so the frontend knows how to render it, and set the agent's output type to a union of all three.
>
> add a tool to my PydanticAI agent that searches my products database and returns real product data, so the agent can only recommend products that actually exist. don't let it hallucinate prices or descriptions.
>
> make the backend run from the backend/folder like this:
> uvicorn main:app --reload --port 8000

**Follow-up prompts:**
1. > update output/harness.md and add a new section titled "How the frontend talks to FastAPI and how the agent is loaded", then put this underneath:
   >
   > _(followed by my notes on how a chat message travels from the website to FastAPI and the agent, and how the agent is loaded)_

2. > yes add those accuracy points. and should the code be changed to gpt-luna-5.6? instead of opus-5.5. make a judgment call and then update it if it should be switched to luna in the code

**Note:** Follow-up 1 was me splitting this problem into two parts: first building the agent backend, then writing up my own notes on how the frontend, FastAPI, and agent connect.

**What the initial prompt lacked:** It didn't name the model to use, so the code kept my earlier Opus 5.5 request even though the Portkey key only serves GPT-5.6 Luna, and it had to be switched in a follow-up.

## Problem 6: Tools: product info and stock

**Initial prompt:**
> create tools to look up info from campus_customs.db, that can pull product description, price, and how many are in stock including by size when the customer asks. the agent should always use the database and never hallucinate products, prices, or quantities. if something is out of stock, indicate clearly that it is out of stock.
>
> after creating the tools, add them to prompts/prompt.md and direct the agent to call them for price and stock questions. update return types in models.py with PriceReply and StockReply too, maybe it's like sub-types under the existing TextReply if possible, if not just keep it separate.
>
> after you're done, give a summary of the tools created and the model fields and rationale for why it was built as it relates to lookups.

**Follow-up prompts:**
1. > FASTER
2. > add a new section to output/harness.md "Tools and model fields chosen" then add this underneath.
   >
   > _(followed by my notes on each tool and the new PriceReply / StockReply model fields)_

**Note:** Follow-up 2 was me splitting this problem into two parts: first building the tools, then writing up my own notes on the tools and model fields chosen.

**What the initial prompt lacked:** It didn't set expectations for speed or scope (e.g. skip extra frontend polish), so I had to tell the agent to go faster mid-task.

## Problem 7: Chat search that updates the page

**Initial prompt:**
> add a feature to the website so that when a user asks if the store has any hoodies, tshirts, etc., the agent should search the catalogue and then the website will dynamically show which products match the user's ask as product cards with the product image, name, price, and a short description. the agent should return structured product matches that the frontend renders on the website. the product cards should still lead to the single-item page when clicked on
>
> after you do this, update prompts/prompt.md and output/harness.md with descriptions of how search results are rendered on the page, adjusting as appropriate for the respective .md's context

**Follow-up prompts:**
_None yet._

**What the initial prompt lacked:** _TBD after any follow-ups._

## Problem 8: Customer memory

**Initial prompt:**
> build on the existing agent and make it so that a shopper can see their chat history and reload it when they return to the site. the chat history must be saved in the database so that it can be reloaded. the agent should know the name and email of the person they're chatting with. guests to the site can still chat but keep the chat history for logged-in users. pick 3 tools that would be helpful for the agent to call but let me know if there's more than 3 that could be useful.
>
> also there has to be page context for the agent, if a human asks if there's another item in pink, the agent should be able to identify which item they're talking about, based on what's seen on the product page.

**Follow-up prompts:**
1. > i like those 3 tools you made. now update output/harness.md with how user chat history is stored, what customer fields the agent can see, and how page context works

**Note:** Follow-up 1 was me splitting this problem into two parts: first building customer memory and page context, then documenting it in harness.md.

## Problem 9: Usability improvements

**Initial prompt:**
> help me think of frontend usability improvements and agent/backend usability improvements. i need to choose 2 of each and then you will execute them. i want to make the site easier to use and i want to make the agent output better or faster or cheaper

**Follow-up prompts:**
1. > and as you build those 4 improvements, please write output/usability.md and document what improvement was added and why it helps a campus customs shopper or the business

**Note:** Follow-up 1 was me splitting this problem into two parts: first choosing and building the improvements, then documenting them in output/usability.md.

## Problem 10: Style the website

**Initial prompt:**
> i want the site design to be inspired by https://fearofgod.com/. it should have closeups of example clothing with a blank background. the design should have minimal copy but make sure the name "Campus Customs" is displayed when the user first opens the site.  the palette leans into muted neutrals, blacks, warm wood tones, and moody monochrome portraits, with the occasional pop of navy blue color from the clothing.
>
> for the font, use Mono in all caps for any titles or menu headings. use a serif font like garamond for body text.
>
> create a bar at the top for the menu that has home, products, about us, login, create account. when you hover over it with the mouse, it should expand into a panel that is semi-opaque with a blurred glass effect. refer to https://fearofgod.com/. for what i mean.

**Follow-up prompts:**
1. > make it so that the menu panel only opens when you hover over the word "products" on the menu. it doesn't make sense that it opens up when you click on home or about us. remove the Campus Customs and Account lists from the menu too. it's redundant because you can click on the those buttons on the exact same page.
   >
   > when the user clicks login, change the bulldog icon to a ink-style drawing of a bulldog.
   >
   > use #2e3135 instead of black on the site.
   >
   > can you use gpt to generate an image of a high fashion model wearing sunglasses and one of the yale clothing items? just one image, for the first photo that the user sees when they open up the site. use my PORTKEY_API_KEY and use gpt-luna-5.6.
2. > if you can't generate an image - just take a screenshot from the HW 3/data/videos/ad_humble.mp4
3. > ok redo the background colors, just use a very dark charcoal black, darker than what it currently is, and fix the colors on the product page. some of the product images look weird and faded. for example in http://localhost:5173/products/football-left-chest-t-shirt the product is totally faded and almost blending into the background. i know you're trying to follow the aesthetic guidelines but it doesn't matter if i can't see what the product is. just stick to using the provided images without editing the colors.
4. > can you just use HW 3/data/videos/ad_humble.mp4 without sound as a video, that loops when the user opens the site? add a semi-opaque box over it, with a subtle film grain, and put the text like Campus Customs, Yale apparel, made to be lived in, Shop the collection, etc etc over it
5. > can you make it so that the video only plays when the person is moving their mouse pointer, and can you make the video a muted desaturated sepia tone? not too orangey brown but muted
6. > like the video "advances" through the loop as the user moves the mouse
7. > for the next part of the page when you scroll down - can you make the product images the same muted sepia tone too, except when the mouse hovers over it, it shows the true product image with the original colors?
8. > looks good but please remove the effect on the Essentials section (the last section when you scroll down the home page)
9. > update output/harness.md with a section on the site design, keep it concise and include why the cool editorial design will draw customers' attention and present campus customs as a high quality, trending brand
10. > open up the html
11. > what sans serif fonts are available for the campus customs
12. > can you show a preview of each one
13. > show in all caps
14. > can you like use html to generate a cool logo for campus customs in some way
15. > yeah replace the text on the front page with the seal superimposed over the video, and then put a shop the collection button underneath

**Note:** Follow-up 9 was me splitting this problem into two parts: first designing and refining the site, then writing up the site design in harness.md.

**What the initial prompt lacked:** It didn't say which menu item should open the panel or what the panel should contain, didn't give an exact background color, didn't specify the hero image or that the login mascot should match the new style, and didn't say the product photos must keep their original colors, so the "monochrome" styling faded some products until a follow-up.

## Problem 11: Site testing (app check)

**Initial prompt:**
> please test the site and put the results into output/app_check.html, include screenshots and concise captions under each one. here's what you need to check:
>
> 1. ask the chat agent to check the inventory level of an item, and then check the given stock quantity and price from the database
> 2. ask the chat agent about the hoodie category and then make sure that the dynamic search-result cards appear on the page in response.
> 3. test the agent to see if there are one-tap starter questions, before the user even types in the chatbox
>
> for the html, make it easy to read and organized for the grader. there should be a heading for each check, a screenshot, and the captions underneath. put the screenshot images in output/app_check_images/ and then link them in app_check.html with relative paths

**Follow-up prompts:**
_None yet._

**What the initial prompt lacked:** _TBD after any follow-ups._

## Problem 12: Audit trail, safety, finish harness

**Initial prompt:**
> create an output/audit_trail.json that tracks the agent-loop activity like time, tool name, short args/result, stop reason, and do not erase it between runs.
>
> put the following safety rules into prompts/prompt.md :
>
> 1. for data handling and privacy - don't expose api keys, minimize collection of personal information, and don't carry sensitive data between unrelated tasks and users.
> 2. decline requests that are not related to clothing at campus customs.
> 3. stop attempting to fulfill a request after 3 failed attempts and create a report for a human to look at.
>
> afterwards, populate output/harness.md so that someone reading it is clear on how the system works. include the following:
>
> * model fields in models.py and why they were chosen
> * tools and abilities
> * safety rules
> * specs like loop limits, caps, models used, how to run front and back

**Follow-up prompts:**
_None yet._

**What the initial prompt lacked:** _TBD after any follow-ups._
