---
version: 1
slug: "templates-pontons-gestionnaire-html"
primary_target: "templates/pontons/gestionnaire.html"
related_targets: ["templates/base.html","templates/pontons/planning.html","templates/pontons/admin/base_admin.html","templates/registration/login.html"]
---

# Surface brief — app shell (gestionnaire, planning, gestion, connexion)

Scope: every authenticated screen plus login. Mode: Operate.
Audience/job: see PRODUCT.md. Primary task: sell / send out / take back a boat in 1–2 taps on a phone in the sun; spot late boats instantly.
Constraints: HTMX/JS contract in AGENTS.md is fixed; no model/URL/business-logic change; one CSS file, one shared JS file, no third party.

## Direction contract

THESIS: Fleet state is river buoyage. Each state is a colour field plus a topmark shape (libre ▲ green, ticket ✕ yellow, sorti ● blue, retard ●● red), never colour alone. Refuses the default: rounded soft cards, stat chips, eyebrows, serif-italic headings.

OWN-WORLD: Near-black shell bars, cool light ground (true black at night), white rows on 1px rules, 4px corners, no glow. Saturated signal colours only for state and for action buttons, where a button wears the colour of the state it produces. One face: Atkinson Hyperlegible Next, tabular figures for every time.

STORY: The operator opens Sorties, reads the red late band first, then the filter bar counts, then each row's state plaque, and taps the one big button on that row. Feedback arrives at the top of the screen and never covers a button.

FIRST VIEWPORT (390px): black top bar (crest, "La Plage", clock); sticky red late band when any boat is late; 5-segment filter bar with counts; pontoon heading; rows 72px: state plaque 70px left, name + big countdown/overrun middle, 52px action button right; libre rows add the client field beside Vendre. Bottom black tab bar, yellow active line, red late badge.

FORM: Buoyage marks (IALA lateral/special/isolated-danger topmarks), assigned candidate 6 of 7. seed:0eb7404b5aa11071
Raises kept from declined challengers: absolute contrast (no mid-grey text on state fields) from datamatics; 1px ruling and square-ish corners instead of shadows from centre-rail setting; whole-cell reflow of the roster from the goods catalog; the number as headline (countdown/overrun is the largest figure in a row) from the factory catalog.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
