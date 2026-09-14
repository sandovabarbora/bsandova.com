# bsandova.com — personal portfolio hub (design)

**Date:** 2026-09-14 · **Replaces:** datasimply.eu as a consulting landing page.

## Intent
datasimply.eu was built as a data-consulting offer for SMBs. The domain now
hosts two research atlases (hockey., football.) and the owner wants the hub to be
a **portfolio**, not a service. New home: **bsandova.com** (to be registered;
Cloudflare Registrar recommended so DNS needs no nameserver change). Deployed via
**Cloudflare Pages** from this repo (static root, no build step).
datasimply.eu becomes a 301 redirect (Cloudflare Redirect Rule) once DNS moves.
hockey.datasimply.eu / football.datasimply.eu stay where they are.

## Identity
Pure quaesitor register *and* palette (`quaesitor/brand/BRAND.md`): parchment /
paper / ink / slate / Review Blue / ochre; Space Grotesk + JetBrains Mono; radius 0;
breakpoints 48rem and 64rem. Mono only for machine-made things (figures, labels).
Not carried over: the `æ` monogram, the bust, the asterisk rule — those are
Quaesitor's marks. What *is* carried over is the technique: the owner's photo
posterised into the same three tones (`assets/posterize.py`), so the portrait
reads as a relief, "White Lotus antiquity, but modern".

Wordmark: `bsandova.com`, lowercase, `.com` in blue.

## Languages
EN default (`index.html`), Czech copy at `cs/index.html`; `hreflang` alternates;
manual translation (the hub is small).

## Structure — one section = one claim = one object, prose ≤ ~600 words
| # | Section | Carries | Object |
|---|---|---|---|
| 1 | Hero | who: Data & Cloud Engineer, Prague; platforms at work, public research otherwise. Lede ≤ 25 words. | 3 mono figure tiles (1.38 NHL/M · 47 spots · 5.7M records), portrait relief |
| 2 | Selected work | 5 cards, ordered by strength: hockey atlas, football atlas, Quaesitor, Brand Reflection Series, tactical-cz. Card = name · year · one finding · stack · live/repo. | card grid |
| 3 | More | FilmRunner, Curio, Pawtrip, Shoptet win-back, second brain, transport sonification | mono table rows |
| 4 | Research & speaking | PCDC 2025, Smart City Expo Barcelona 2024, Quaesitor preprint, IT SPY nominee 2025, IES thesis | list with years |
| 5 | Now + footer | Alma Career one-liner, three working principles as mono bullets, email, one sentence "open to collaboration and selected consulting", entity line | — |

Rules: every figure on the page links to the artifact that produced it; no
Golemio/ČSFD numbers (unverified); no fictional case studies; hazard red never
used decoratively; no em dashes in copy.

## Motion
`fadeUp` on section entry via scroll timeline, `growX` for any bars, JS parallax
on the portrait (rAF). All off under `prefers-reduced-motion`. No GSAP.

## Process
Hero first → screenshot → approve → sections 2–5 one at a time → `cs/` → redirect.
