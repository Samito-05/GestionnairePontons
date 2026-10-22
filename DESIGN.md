---
name: La Plage — L'Isle-Adam
description: Operator board, planning and admin for hourly boat rentals, drawn as river buoyage.
colors:
  libre: "#075c2f"
  ticket: "#ffd100"
  sortie: "#0b4a9e"
  retard: "#a50018"
  signal: "#ffd100"
  shell: "#0d1114"
  shell-2: "#20272d"
  shell-ink-2: "#b8c2ca"
  ground: "#eef1f3"
  surface: "#ffffff"
  surface-2: "#f5f7f8"
  rule: "#cdd4da"
  rule-strong: "#9aa6af"
  ink: "#0d1114"
  ink-2: "#3b444c"
  ink-3: "#56616b"
  ticket-text: "#6b4f00"
  retard-wash: "#fde8ea"
  ground-night: "#000000"
  surface-night: "#111518"
  ink-night: "#f2f5f7"
typography:
  headline:
    fontFamily: "Atkinson Next, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  figure:
    fontFamily: "Atkinson Next, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 800
    lineHeight: 1.15
    fontFeature: "\"tnum\""
  title:
    fontFamily: "Atkinson Next, system-ui, sans-serif"
    fontSize: "1.1rem"
    fontWeight: 800
    lineHeight: 1.2
  body:
    fontFamily: "Atkinson Next, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.4
    fontFeature: "\"tnum\""
  label:
    fontFamily: "Atkinson Next, system-ui, sans-serif"
    fontSize: "0.82rem"
    fontWeight: 800
    lineHeight: 1.2
rounded:
  tick: "2px"
  base: "4px"
spacing:
  bar: "56px"
  band: "52px"
  tab: "64px"
  row: "72px"
  plaque: "74px"
  target: "48px"
components:
  button-vendre:
    backgroundColor: "{colors.ticket}"
    textColor: "{colors.ink}"
    rounded: "{rounded.base}"
    height: "52px"
    padding: "0 1rem"
  button-sortir:
    backgroundColor: "{colors.sortie}"
    textColor: "{colors.surface}"
    rounded: "{rounded.base}"
    height: "52px"
    padding: "0 1rem"
  button-retour:
    backgroundColor: "{colors.libre}"
    textColor: "{colors.surface}"
    rounded: "{rounded.base}"
    height: "52px"
    padding: "0 1rem"
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.surface}"
    rounded: "{rounded.base}"
    height: "44px"
    padding: "0 1rem"
  button-ghost:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.base}"
    height: "44px"
    padding: "0 1rem"
  button-danger-solid:
    backgroundColor: "{colors.retard}"
    textColor: "{colors.surface}"
    rounded: "{rounded.base}"
    height: "44px"
    padding: "0 1rem"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.base}"
    height: "48px"
    padding: "0.6rem 0.8rem"
  state-plaque-libre:
    backgroundColor: "{colors.libre}"
    textColor: "{colors.surface}"
    typography: "{typography.label}"
    width: "{spacing.plaque}"
  state-plaque-ticket:
    backgroundColor: "{colors.ticket}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    width: "{spacing.plaque}"
  state-plaque-sortie:
    backgroundColor: "{colors.sortie}"
    textColor: "{colors.surface}"
    typography: "{typography.label}"
    width: "{spacing.plaque}"
  state-plaque-retard:
    backgroundColor: "{colors.retard}"
    textColor: "{colors.surface}"
    typography: "{typography.label}"
    width: "{spacing.plaque}"
  late-band:
    backgroundColor: "{colors.retard}"
    textColor: "{colors.surface}"
    height: "{spacing.band}"
    padding: "0 1rem"
  topbar:
    backgroundColor: "{colors.shell}"
    textColor: "{colors.surface}"
    height: "{spacing.bar}"
  filter-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.surface}"
    height: "60px"
---

# Design System: La Plage — L'Isle-Adam

## Overview

**Creative North Star: "River Buoyage"**

Every boat state is a navigation mark: a saturated colour field plus a topmark shape, read at arm's length in sunlight. Libre is a green triangle (▲), a sold ticket is a yellow saltire (✕), a boat out is a blue disc (●), a late boat is the isolated-danger double disc (●●) on red. The shapes come from IALA lateral, special and isolated-danger topmarks and live in the SVG sprite as `m-libre`, `m-ticket`, `m-sortie`, `m-retard`. Colour and shape always travel together.

The world is a working instrument, not a showcase. Near-black shell bars frame a cool, pale ground by day and true black at night; content sits on white surfaces separated by 1px rules with 4px corners. Saturated colour is spent only on state and on the operator actions that change state, and each action button wears the colour of the state it produces. One typeface, Atkinson Hyperlegible Next, at heavy weights, with tabular figures everywhere so times and countdowns never jitter. Density is high and honest: the number (countdown or overrun) is the biggest thing in a row.

Lateness outranks everything. A late boat turns its row's plaque red with the double-disc mark, washes the row pink (dark red at night) inside a 2px red line, raises a sticky red band under the top bar, puts a red count on the filter bar and a red badge on the bottom tab, and paints red/black hazard stripes on the planning timeline.

**Key Characteristics:**
- State = colour field + buoyage topmark, never colour alone.
- Action buttons carry the colour of the state they produce (Vendre yellow, Sortir blue, Retour green).
- Black shell, pale cool ground, white surfaces on 1px rules, 4px corners; no shadows on resting content.
- One face (Atkinson Next), weights 400 to 800, tabular figures globally.
- Day and night themes share the same saturated signal fields; only grounds, inks and on-surface state text change.
- Signal yellow is the shell's only accent: active tab/nav line, focus on black, day marker, the toast action.

## Colors

A neutral, cool-grey instrument panel with four saturated buoyage signals and one signal yellow; all signal fields meet 7:1 against their ink.

### Primary
- **Port Green / Libre** (`libre`): the free state. Plaque field, triangle mark, and the Retour button (returning a boat makes it libre). On light surfaces as text it stays the same green; at night the on-surface text lifts to a brighter green (#3cc47a).
- **Special-Mark Yellow / Ticket** (`ticket`): ticket sold, boat reserved. Plaque field with black ink, saltire mark, the Vendre button, and the yellow hatching on the planning. On light surfaces yellow is never used as text; the on-surface variant is a dark ochre (`ticket-text`).
- **Starboard Blue / Sortie** (`sortie`): boat on the water. Plaque field, disc mark, Sortir button, and the solid rental block on the timeline. Also the light-theme link and focus colour.
- **Isolated-Danger Red / Retard** (`retard`): late boat and destructive action. Plaque, late band, tab badge, solid danger button, error toast, overtime stripes (alternating with a near-black red #1a0004). Light wash (`retard-wash`) fills a late row and error notices.

### Secondary
- **Signal Yellow** (`signal`): the same yellow as the ticket field, used as the shell's accent: 3px active line under top-nav items and over the active bottom tab, focus ring on black surfaces and on the whole night theme, the day-change tick on the time axis, the "Annuler" toast action, the brief ring flash on a swapped row, and the solid top-bar button.

### Neutral
- **Hull Black** (`shell`): top bar, bottom tab bar, login backdrop; pure black (#000000) at night. Hover inside the shell uses `shell-2`; secondary shell text uses `shell-ink-2`.
- **River Mist** (`ground`): page ground behind every surface; `ground-night` at night.
- **White Board** (`surface`): rows, panels, tables, forms, dialogs; `surface-night` at night. `surface-2` is the recessed tone for toolbars, table heads, hovers and axis rows.
- **Rules** (`rule`, `rule-strong`): 1px dividers between rows and panels; the strong rule outlines inputs, ghost buttons, dialogs and the timeline label column.
- **Inks** (`ink`, `ink-2`, `ink-3`): primary text (`ink-night` at night), secondary meta text, and the quietest helper/placeholder text. `ink-3` is the floor; nothing lighter carries text.

### Named Rules
**The Buoyage Rule.** A state is always a colour field and its topmark together. A new state indicator that shows colour without the mark, or the mark in a colour other than its state, is wrong.

**The Produced-State Rule.** An operator action button wears the colour of the state it creates: Vendre = ticket yellow, Sortir = sortie blue, Retour = libre green. Never colour an action by urgency or brand.

**The Signal-Budget Rule.** Saturated colour appears only on state, on state-producing actions, on the late alarm, and on the shell's yellow accent line. Everything else is neutral ink on white.

**The Same-Signal-At-Night Rule.** The four state fields keep their day values in the dark theme; only grounds, inks, on-surface state text and the focus colour (to yellow) change.

## Typography

**Display Font:** none (no display face)
**Body Font:** Atkinson Next (Atkinson Hyperlegible Next, self-hosted variable woff2, weights 200–800) with system-ui, -apple-system, Segoe UI, sans-serif
**Label/Mono Font:** same face; tabular figures (`font-variant-numeric: tabular-nums`) are set on `body` and inherit everywhere.

**Character:** A legibility face built for low-vision reading, set heavy. Headings, names, numbers, labels and buttons all run at 800; body and meta at 400–700. No italics, no serif, no uppercase labels.

### Hierarchy
- **Headline** (800, 1.5rem, 1.3rem under 768px, 1.2): page titles. An optional subtitle line sits under the title at 0.9rem / 600 in `ink-3`.
- **Clock** (800, 1.6rem / 1.35rem in the mobile bar, 1): live time in page headers and the mobile top bar.
- **Figure** (800, 1.25rem, 1.15): the countdown ("reste 51 min") or overrun ("+46 min") in a row; filter counts at 1.45rem. The number is the headline of its row.
- **Title** (800, 1.1rem): boat names in rows; section titles at 1.05rem; dialog titles 1.15rem.
- **Body** (400, 16px, 1.4): default text; meta lines 0.92rem in `ink-2`.
- **Label** (800, 0.82rem): state plaque words (Libre, Ticket, Sorti, Retard), badges (0.8rem), tab labels (0.82rem / 700), table heads (0.86rem). Sentence case.

### Named Rules
**The One-Face Rule.** Atkinson Next is the only typeface. Hierarchy comes from size and weight (400/600/700/800), never from a second family, italics or uppercase tracking.

**The Tabular Rule.** Every time, count and duration is set in tabular figures. Do not override `font-variant-numeric` locally.

## Layout

Single column of content in a 1440px max container (1.5rem side padding; 0.75rem under 768px), under a sticky 56px black top bar. On phones (≤768px) gestionnaire and admin get a fixed 64px black bottom tab bar (plus safe-area inset); the top nav collapses and the clock moves into the bar.

The operator board stacks: sticky red late band (52px, only when a boat is late) directly under the top bar; a 5-column filter bar (Tous, Libres, Tickets, Sortis, Retards, count above label, 60px tall); then pontoon sections. Rows auto-fill in columns of min 380px on wide screens with 0.5rem gaps; on phones they run edge to edge, separated by 1px rules (gap 1px over a rule-coloured background), no side borders or corners. Below 360px filter labels drop to marks only.

A row is a three-column grid: 74px state plaque | name, figure and meta | action button (min 108 × 52px). A libre row adds a second line where the client field and Vendre share the width beside the plaque.

The planning is a horizontal timeline: sticky 248px label column (150px on mobile), 36px hour axis, 34px pontoon rows, 58px boat rows (52px mobile), hour lines at full rule, half-hours at 45% opacity, a 2px ink now-line with a black time pill. Mobile offers a two-way segmented switch between tiles and timeline.

Admin uses a 220px left sidebar (190px under 1024px) beside the main area; on phones the sidebar becomes a sticky horizontal scrolling tab strip and tables reflow into 3-column cards with `data-label` captions.

## Elevation & Depth

Flat. Resting content is separated by 1px rules and the ground/surface tone step, never by shadow. Depth appears only on layers that float above the page: toasts and the confirm dialog. Active and current states are drawn as inset 3px lines, not raised.

### Shadow Vocabulary
- **Floating toast** (`box-shadow: 0 8px 24px rgb(0 0 0 / .28)`): toasts only.
- **Dialog** (`box-shadow: 0 16px 48px rgb(0 0 0 / .35)`, backdrop `rgb(5 8 10 / .6)`): the confirm dialog only.
- **Current-item line** (`box-shadow: inset 0 -3px 0 var(--signal)` / `inset 0 3px 0` on tabs): active nav item, active tab; admin mobile strip uses an ink line.
- **Swap flash** (`0 0 0 4px var(--signal)` fading to none over 0.7s): a row just replaced by HTMX; held static at 3px under reduced motion.

### Named Rules
**The Ruled-Not-Raised Rule.** Rows, panels, tables and forms sit on 1px rules with no shadow. Shadow is reserved for what floats above the page (toast, dialog).

## Shapes

Square-ish and engineered. One corner radius (4px) for rows, buttons, inputs, toasts and dialogs; 2px for small marks (badges, timeline rental blocks, the boat's own colour chip); panels, tables, filter bars, segmented controls and the late band are square. On phones the operator rows lose their corners and run flush. Circles are reserved for meaning: the disc is the "sorti" topmark, so a boat's own colour chip is a 10px square with 2px corners, never a dot. The one pill is the red late-count badge on the bottom tab. Hazard stripes run at -45°: yellow hatching (3px on 9px) for a sold ticket, red/black (6px/4px) for overtime.

## Components

### Buttons
Heavy, flat, rectangular; labels at 800.
- **Shape:** gently squared (4px), 1px border, min-height 44px (36px small, 52px large and in rows).
- **Operator actions:** Vendre (ticket yellow, black ink), Sortir (sortie blue, white), Retour (libre green, white); 52px tall and at least 108px wide in rows.
- **Primary:** ink fill with surface text; hover brightens (dims at night).
- **Ghost:** white with a strong-rule border; hover to `surface-2`.
- **Danger:** ghost with red text, wash on hover; **Danger solid:** red fill, used in the confirm dialog.
- **Busy:** during an HTMX request the button drops to 55% opacity with a progress cursor and ignores input.
- **Focus:** 3px focus outline (blue by day, yellow at night and on black surfaces), offset 2px.

### State plaque (signature)
The left 74px column of every boat row: full-height state field, topmark above the word, label typography. Libre green ▲ "Libre", ticket yellow ✕ "Ticket", sortie blue ● "Sorti", retard red ●● "Retard". On a libre row it spans both lines.

### Boat row
White surface, 1px rule, 4px corners (flush on phones), min 72px. Body holds the name with its colour chip, the figure (countdown or overrun) and a meta line ("fin 10:33 · client", "vendu 09:14 · client"). Late: pink wash, 2px red line, red overrun figure. Rows carry `data-statut` and `is-late`; filters and counters read those.

### Late band
Full-width red bar, sticky under the top bar, ●● mark, boat name and overrun, "Voir" link on the right. Toasts drop below it on phones so feedback never covers it.

### Filter bar
Five equal cells on one white strip divided by 1px rules: big count over a mark plus label. Pressed cell inverts to ink; the Retards cell turns its count red and, when pressed, fills red.

### Chips / badges
Small 2px-cornered labels at 0.8rem / 800: neutral (surface-2 with rule border), or filled with a state colour plus its mark.

### Inputs / Fields
- **Style:** white field, 1px strong-rule border, 4px corners, min-height 48px, 1rem text; selects carry an inline chevron.
- **Focus:** border and outline switch to the focus colour, outline offset 0.
- **Error:** 2px red border, red message with the retard mark beneath the field. In rows the client field sits on `surface-2` at 52px.

### Cards / Containers
Panels, form panels, tables and the timeline container: white, 1px rule, square, no shadow. Panel titles sit on a ruled header; link lists are 48px ruled rows with the count right-aligned.

### Navigation
Black top bar: crest and "La Plage" with a small second line, nav items in `shell-ink-2` at 700, current item white with a 3px yellow underline. Mobile: black bottom tab bar, current tab white with a 3px yellow line on top, red count badge for late boats. Admin sidebar: 44px links, current link inverted to ink.

### Feedback
Toasts float top-right (full width on phones) under the bar: ink surface with a state mark in an on-ink colour, 56px tall, 48px close target; error toasts are red; the return toast carries a yellow "Annuler" button. Destructive confirmation uses a 440px dialog titled with the retard mark. In-page notices are ruled boxes on `surface-2`, red wash for errors.

### Planning timeline
Rental blocks: sortie blue, 2px corners, white time label; returned blocks turn neutral with a strong-rule inset. Overtime extends in red/black stripes; sold tickets show as yellow hatching from the sale time. Legend repeats the same marks and swatches.

## Do's and Don'ts

### Do:
- **Do** pair every state colour with its topmark from the sprite (`m-libre` ▲, `m-ticket` ✕, `m-sortie` ●, `m-retard` ●●).
- **Do** colour an action button with the state it produces (Vendre yellow, Sortir blue, Retour green).
- **Do** use `ticket-text` (dark ochre) for ticket wording on light surfaces; reserve the yellow field for fills and the shell accent.
- **Do** separate content with 1px rules and the ground/surface tone step; keep shadows to toasts and the dialog.
- **Do** make the countdown or overrun the largest figure in a row, in tabular figures.
- **Do** keep operator action targets at 52px in rows and every touch target at least 48px.
- **Do** give anything late the full red treatment: plaque, wash and 2px line, band, filter count, tab badge, stripes.
- **Do** mark current navigation with a 3px signal-yellow line on the shell.

### Don't:
- **Don't** show a state by colour alone, or reuse a state colour for anything that is not that state or its producing action.
- **Don't** draw a boat's own colour as a circle; the disc means "sorti".
- **Don't** add a second typeface, italics or uppercase tracked labels.
- **Don't** put mid-grey text on a state field; plaque ink is white, or black on yellow.
- **Don't** lift resting rows, panels or tables with shadows or glow.
- **Don't** load fonts, icons or styles from a third party; icons come from the inline SVG sprite.
