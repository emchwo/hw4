# Site design

## Direction

Editorial streetwear, inspired by Fear of God: minimal copy, big imagery, lots of negative space, and a tight palette. The goal is for Campus Customs to read as a high-quality, current brand rather than standard school merch.

## Palette

| Role | Color |
|---|---|
| Background | very dark charcoal `#161719` (raised surfaces `#1e2023`, `#27292d`) |
| Text | bone `#ebe5db`, muted `#9a9389` |
| Neutrals | stone `#d6cfc3` |
| Warm wood accents | walnut `#8a6a4b`, oak `#b8946f` (thin rules and dividers) |
| Navy | `#1d3557`; mostly comes from the clothing itself, plus the chat button |

## Type

- **Titles, menus, labels:** IBM Plex Mono, all caps, wide letter-spacing
- **Body text:** EB Garamond (serif)
- Both load from Google Fonts

## Key pieces

- **Intro:** "CAMPUS CUSTOMS" fills the screen for a moment on first open (once per session)
- **Home hero:**
  - The Campus Customs ad plays full-screen as a muted, desaturated sepia video
  - It doesn't play by itself; it scrubs forward through the loop as the mouse moves
  - The **Campus Customs seal** (an SVG logo: double ring with "CAMPUS CUSTOMS · NEW HAVEN, CT", an italic "CC", a wood rule, and a navy dot) is centered over the video, with a "Shop the collection" button below it
- **Category tiles:** six closeups (hoodies, crewnecks, quarter-zips, T-shirts, jackets, long sleeve) in sepia; hovering shows the original colors
- **Menu:**
  - A thin bar: Home, Products, About Us on the left; the brand centered; Log In and Create Account on the right
  - Hovering **Products** expands a frosted-glass panel with the shop categories and a feature tile
- **Product imagery:**
  - Photos are shown in their original colors
  - Each frame is painted with the photo's own background color, so garments sit on a seamless blank backdrop
- **Login panel:** an ink-style drawing of Handsome Dan, the Yale bulldog (SVG)
- **Chat:**
  - A square, glassy panel with mono labels
  - Stock answers show a color-coded size grid, price answers show a mini price card, and search results fill the Products page

## Why it works

- **Grabs attention:** the mouse-driven video and cinematic sepia feel like a fashion campaign, so shoppers stop and explore
- **Signals quality:** restraint (few words, generous space, refined type) is the visual language of premium brands
- **Feels current:** mono type, frosted glass, and moody editorial imagery borrow from today's streetwear labels
- **Keeps products central:** with minimal copy, the clothing does the talking, and true-color photos show exactly what shoppers are buying

All visuals are built in HTML, CSS, and SVG. The only media files are the hero video and its poster frame, both taken from the Campus Customs ad.
