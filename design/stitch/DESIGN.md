I'm designing a web app called Forecastly — a demand-forecasting dashboard for
restaurant managers. The user is a non-technical restaurant owner or manager who
wants a fast, clear answer to one question: "What am I likely to sell over the
next 7 days?" Design for desktop-first but fully responsive to tablet and mobile.
Product tone: trustworthy, calm, modern SaaS — not a spreadsheet, not a science
tool. Prioritize clarity over analytics density. Never expose model names, model
competitions, job queues, or config to the primary view.
Visual style:
- Clean, spacious, data-forward. Generous whitespace. Rounded-2xl cards with soft,
  low-spread shadows and hairline borders. 8pt spacing rhythm.
- Palette: primary deep teal/emerald (#0F766E), warm amber accent for highlights
  and calls-to-action emphasis (#F59E0B), neutral slate grays for text and
  surfaces. Success green, warning amber, error red used sparingly.
- Support both light and dark mode. Light = near-white surfaces on a faint gray
  canvas. Dark = slate-900 canvas, slate-800 cards.
- Typography: one clean geometric sans (Inter or Geist) for both headings and
  body. Big, confident section titles. Tabular numerals for all metrics and table
  figures.
- Charts: minimal, muted gridlines, rounded bars / smooth lines, clear legends,
  hover tooltips. No 3D, no heavy gradients.
- Buttons: solid teal primary, outline secondary, subtle ghost tertiary.
- Empty states: friendly illustration + one-line explanation + single clear action.
Global chrome: a slim top header with the "Forecastly" wordmark on the left and a
user/account menu on the right. Max content width ~1100px, centered.