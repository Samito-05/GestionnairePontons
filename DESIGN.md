---
name: La Plage — L'Isle-Adam
description: Operator board, planning and admin for hourly boat rentals, in the colours of the city of L'Isle-Adam.
colors:
  shell: "#005378"
  shell-2: "#186485"
  shell-ink-2: "#d6e8f0"
  accent: "#00abc2"
  link: "#3b29ff"
  ground: "#f3eee4"
  surface: "#fffdf8"
  surface-2: "#f8f4ea"
  rule: "#ddd5c3"
  rule-strong: "#a99f8a"
  ink: "#102a43"
  ink-2: "#34495e"
  ink-3: "#4a6278"
  libre: "#b8ecf3"
  libre-ink: "#00424d"
  ticket: "#fde3a8"
  ticket-ink: "#5a3a05"
  sortie: "#d9d5ff"
  sortie-ink: "#1d10a0"
  retard: "#f4b3a4"
  retard-ink: "#6e1a0a"
  signal: "#f0a531"
typography:
  display:
    fontFamily: "Fraunces, Georgia, serif"
    fontWeight: 700
    lineHeight: 1.2
  body:
    fontFamily: "Figtree, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.4
    fontFeature: "\"tnum\""
rounded:
  base: "12px"
  button: "9px"
spacing:
  bar: "56px"
  tab: "64px"
  row: "72px"
  plaque: "74px"
  target: "48px"
---

# Design System: La Plage — L'Isle-Adam

## Overview

Light only (`color-scheme: light`, no theme toggle). Sand ground, cream surfaces, marine ink, and the city's palette on the shell: petrol bar, turquoise accent, indigo links and focus. Fonts are self-hosted: Fraunces for headings and figures of the clock, Figtree for everything else. Corners are rounded (12 px panels and rows, 9 px buttons), shadows are soft and used only on panels, rows and the login card.

## Colors

- **Shell** (`#005378`, hover `#186485`): top bar, bottom tab bar, login header. Active nav item: 3 px line in `signal`.
- **Accent turquoise** (`#00abc2`): top border of empty states.
- **Indigo** (`#3b29ff`): links and focus ring.
- **Ground / surface**: sand `#f3eee4`, cream `#fffdf8`, `surface-2` for inputs and panel headers.
- **Fleet states** are pastel fields with dark ink (contrast ≥ 7:1), always labelled in words, never colour alone and no pictograms: libre = turquoise, ticket = cream yellow (the city has no yellow), sorti = indigo tint, retard = coral. The state's own colour is worn by the button that produces it: Vendre → ticket, Sortir → sorti, Retour → libre. Retard also gets a red outline and a `retard-wash` row.
- State **text** on light surfaces uses the saturated variants (`libre-text`, `ticket-text`, `sortie-text`, `retard-text`).

## Typography

Fraunces 700 on `h1`–`h3`, brand name, clock and boat names. Figtree for body, labels and buttons (800 for buttons and figures). Tabular figures everywhere.

## Layout

Mobile first: rows are plaque `74px` | body | action, action buttons ≥ 48 px (52 px on the board). Bottom tab bar on mobile for gestionnaire and admin; the admin sidebar becomes a scrollable tab strip. Two columns of rows from tablet width up.

## Components

- **Buttons**: `.btn-vendre`, `.btn-sortir`, `.btn-retour` (pastel + 1 px inset edge), `.btn-primary` (ink), `.btn-ghost`, `.btn-danger` / `.btn-danger-solid`.
- **State plaque**: text label only (Libre · Ticket · Sorti · Retard), pastel field, 1 px edge on its right side.
- **Late band, filter bar, badges**: same pastel fields; the active filter is ink on cream.
- **Planning timeline**: running rental = indigo tint block, returned = neutral, overtime = red/black stripes, ticket = amber hatching.
- **Login**: marine header with the coat of arms, cream card, city logo footer.

## Do's and Don'ts

- **Do** keep every state readable in words and at ≥ 7:1 contrast.
- **Do** keep the city palette on the shell and links; leave state colours to the four state fields.
- **Don't** reintroduce dark mode, pictograms for states, third-party fonts or CDNs.
- **Don't** use red for anything but lateness and destructive actions.
