# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Gestionnaire** (primary): works on the pontoon, outdoors, often in direct sun, sometimes with wet hands, with customers waiting. Uses a personal/work phone (Android or iPhone, browser or installed PWA) or a shared tablet at the pontoon, depending on the post. Job: sell a ticket, send a boat out, take it back, in one or two taps, and see at a glance what is free, ticketed, out and above all late.
- **Admin**: at the office, on desktop. Job: create/edit/delete pontoons, boats, rentals and users quickly; read tables, fill short forms, fix validation errors next to the field.
- **Visiteur**: read-only planning (desktop timeline + mobile view). Job: understand in three seconds what is available and when.

## Product Purpose

Run hourly rentals of small watercraft (pédalos, kayaks, canoës, SUP, barques) across several pontoons for "La Plage — L'Isle-Adam". Success: no double booking, no boat forgotten on the water, a queue that moves fast.

## Operating Context

- Season fleet: medium, 15–40 boats over several pontoons; the operator board scrolls.
- Several operators work at once; boards refresh live without reload (HTMX / soft refresh).
- Quick rental state machine: libre, reservee (ticket sold), sortie (out), back to libre on return. A sortie past its scheduled end and not returned is late ("Retard +N min").
- A return can be undone for 60 s.

## Capabilities and Constraints

- Django 5.2 templates + HTMX (vendored) + one CSS file (`static/css/base.css`) + one shared JS file (`static/js/app.js`). No CSS/JS framework, no CDN (RGPD): fonts self-hosted, icons in an inline SVG sprite.
- In production: models, URLs and business logic stay unchanged; the HTMX/JS contract (ids, data attributes, partial names, `HX-Trigger: retourFait`) is fixed. See AGENTS.md.
- All UI text in French.

## Brand Commitments

- Name "La Plage — L'Isle-Adam" stays.
- Town crest `static/icons/blason.png` stays visible; town logo `static/icons/logo-ville.svg` (raster JPEG wrapped in SVG) is an available asset.
- PWA icons `icon-192.png` / `icon-512.png` stay as they are.

## Evidence on Hand

Demo data only (`init_demo`). No real usage metrics, testimonials or photos; do not fabricate any.

## Product Principles

1. The fleet state reads at arm's length in sunlight: state never relies on colour alone.
2. The main action for a boat is always visible, never in a menu, and acknowledges instantly.
3. Late boats outrank everything else on every operator screen.
4. Admin is a tool, not a showcase: dense, sortable-looking tables, short forms.
5. Nothing loads from a third party.

## Accessibility & Inclusion

WCAG AA minimum, AAA targeted for fleet-state colours. Touch targets ≥ 48 px for operator actions. Visible keyboard focus, `aria-pressed` on filters, `prefers-reduced-motion` honoured.
