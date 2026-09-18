# PollTrust — DESIGN.md

> **Design direction:** Pirsch Analytics-style data presentation with the Idle Finance color system, adapted for a Hebrew RTL polling-analysis product.

## 1. Design Intent

PollTrust should feel like a serious, modern analytics product: calm, precise, data-forward, and easy to scan.

The design combines two references deliberately:

- **Pirsch Analytics** supplies the **information presentation language**:
  - clear metric hierarchy;
  - flat, bordered data surfaces;
  - compact filter / tab controls;
  - strong grouping without excessive visual chrome;
  - analytics that remain readable at a glance;
  - generous spacing around dense information;
  - data itself as the visual focus.

- **Idle Finance** supplies the **color and surface language**:
  - deep navy canvas;
  - one-step-lighter navy panels;
  - white / fog-gray text hierarchy;
  - electric cyan as the primary UI accent;
  - hairline borders instead of shadows;
  - dark, data-terminal atmosphere.

Do **not** copy either site literally. PollTrust is a Hebrew RTL public data product, not a crypto interface or a marketing site.

---

## 2. Core Principles

### Data first
Numbers, comparisons, labels, and trends are the primary visual content. Decorative elements must not compete with them.

### Calm density
PollTrust contains substantial information. Keep it compact enough to compare quickly, but use spacing and grouping so it never feels cramped.

### Flat hierarchy
Use surface contrast, 1px borders, spacing, type hierarchy, and accent color instead of drop shadows, glassmorphism, blur, excessive gradients, or nested cards inside cards.

### Progressive disclosure
Show the most important comparison first. Detailed party numbers, methodology, support counts, and secondary metrics can sit one level deeper.

### RTL-native
The interface must look intentionally designed for Hebrew, not mirrored from an LTR layout after the fact.

---

## 3. Color System

The interface palette is based on Idle Finance.

| Name | Value | Token | Role |
|---|---|---|---|
| Abyss Navy | `#17202E` | `--color-bg` | Main page canvas |
| Tide Card | `#202A3E` | `--color-surface` | Cards, tables, grouped analytics surfaces |
| Tide Raised | `#263249` | `--color-surface-raised` | Selected rows, hover surfaces, nested controls |
| Spectral Cyan | `#6AE4FF` | `--color-accent` | Primary UI accent, focus, selected state, chart highlight |
| Bone White | `#FFFFFF` | `--color-text-primary` | Main text, metric values, headings |
| Fog Gray | `#CDD0D6` | `--color-text-secondary` | Secondary text and explanations |
| Muted Slate | `#9098A6` | `--color-text-muted` | Metadata, disabled labels, low-priority information |
| Carbon | `#0B1018` | `--color-border-strong` | Strong structural border |
| Hairline | `#334056` | `--color-border` | Default borders and dividers |

### Accent discipline

Spectral Cyan `#6AE4FF` is the **interface accent**, not a general fill color.

Use it for active tabs, focused controls, selected filters, important icons, chart emphasis, links, and thin strokes.

Do not fill large content areas with cyan, use cyan behind long text, make every metric cyan, or turn every button into a cyan block.

---

## 4. Semantic Data Colors

PollTrust already uses colors to represent political blocs. These colors are semantic data and must remain separate from the interface palette.

The Idle Finance palette governs **UI chrome**. Bloc colors govern **poll data**.

| Meaning | Value | Token |
|---|---|---|
| Change / opposition bloc | `#4F8CFF` | `--color-bloc-change` |
| Current coalition bloc | `#FF627D` | `--color-bloc-coalition` |
| Neither / unaligned | `#8B95A5` | `--color-bloc-neutral` |

Rules:
- Always accompany bloc color with a text label and numeric value.
- Never rely on color alone.
- Do not use Spectral Cyan as a political bloc color.
- Keep political colors inside charts, party rows, dots, bars, legends, and bloc summaries rather than global navigation.

---

## 5. Surfaces & Elevation

| Level | Surface | Usage |
|---|---|---|
| 0 | `#17202E` | Page background |
| 1 | `#202A3E` | Main analytics panels, cards, table surfaces |
| 2 | `#263249` | Hover, selected states, nested controls |
| Accent | `#6AE4FF` | Thin emphasis only |

Do not use normal box shadows.

Depth comes from:
1. a slightly lighter surface;
2. a 1px border;
3. spacing;
4. active-state color.

Default structural border:

```css
border: 1px solid #334056;
```

Avoid:

```css
box-shadow: 0 20px 50px ...;
backdrop-filter: blur(...);
```

---

## 6. Typography

PollTrust is Hebrew-first, so typography must prioritize excellent Hebrew rendering.

Use:

```css
font-family:
  "Heebo",
  "Noto Sans Hebrew",
  "Arial Hebrew",
  Arial,
  sans-serif;
```

**Heebo** is preferred because it is clean, contemporary, highly readable in Hebrew, and works well with dense numeric interfaces.

Weights:
- 400 — body copy, metadata
- 500 — labels, tabs, controls
- 600 — metric labels and section titles
- 700 — major headings and primary values

Avoid overly heavy 800–900 weights.

| Role | Desktop | Mobile | Weight |
|---|---:|---:|---:|
| Page title | 40px | 30px | 700 |
| Section title | 28px | 24px | 700 |
| Panel title | 20px | 18px | 600 |
| Primary metric | 32–40px | 28–34px | 700 |
| Body | 16px | 16px | 400 |
| Small body | 14px | 14px | 400 |
| Caption / metadata | 12–13px | 12–13px | 500 |

Use:

```css
font-variant-numeric: tabular-nums;
```

for comparable numbers.

Do not copy Idle Finance's 56–100px marketing typography into the analytics interface.

---

## 7. Spacing System

Use a 4px base with an 8px dominant rhythm:

```text
4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80
```

Recommended:
- page horizontal padding: 24–32px desktop, 16px mobile;
- panel padding: 20–24px;
- section gap: 48–64px;
- panel gap: 16–24px;
- inline control gap: 8px;
- row height: 44–52px;
- chart-to-label gap: 12–16px.

PollTrust should feel **compact but not compressed**.

---

## 8. Shape System

Pirsch's broad rounded-card feel is useful, but PollTrust should be slightly more restrained.

| Element | Radius |
|---|---:|
| Main cards / panels | 14–16px |
| Small cards | 10–12px |
| Inputs | 8px |
| Buttons | 10–12px |
| Pills / filters | 999px |
| Table container | 14–16px |

Avoid making every container a pill.

---

## 9. Analytics Presentation

This is the primary design language borrowed from Pirsch Analytics.

### Summary metrics

Primary metrics should use a simple number-over-label pattern.

Example:

```text
11.4
שגיאת מנדטים צפויה

5
מערכות בחירות
```

Rules:
- large numeric value;
- short muted label;
- no decorative icon unless it communicates actual meaning;
- no separate card for every minor metric if several metrics belong to one analytical group.

A group of metrics may share one parent surface.

### Analytics panels

Each major analytical unit should follow:

1. title;
2. optional one-line explanation;
3. primary visualization or values;
4. small metadata / support line.

### Charts

Charts should be visually quiet.

Use:
- thin grid lines;
- restrained axes;
- labels outside bars where possible;
- direct labeling instead of oversized legends;
- one cyan highlight for interaction/selection;
- semantic political colors only when the plotted data actually represents blocs/parties.

Avoid:
- 3D effects;
- gradients inside bars;
- glowing chart lines;
- oversized legends;
- chart backgrounds different from the parent surface.

### Tables

Tables are first-class analytics surfaces, not fallback UI.

Style:
- surface: `#202A3E`;
- 1px separators: `#334056`;
- subtle row hover: `#263249`;
- primary values in Bone White;
- secondary/support data in Fog Gray;
- numeric values aligned consistently;
- tabular numerals;
- headers visually quieter than values.

For the historical PollTrust table:
- keep the pollster identity column sticky on narrow screens;
- use `position: sticky` on the RTL/right edge;
- sticky cells must have opaque `#202A3E` background;
- use a divider at the sticky edge;
- maintain readable row heights on mobile.

### Filters and controls

Use Pirsch-like compact filter semantics with Idle colors.

Inactive:
- transparent or Tide surface;
- Fog Gray text;
- 1px Hairline border.

Active:
- Tide Raised background;
- Spectral Cyan text or border.

Do not make every filter a bright cyan filled pill.

---

## 10. Current Polls Screen

The screen should answer, in this order:

1. What is the overall current picture?
2. How do pollsters differ?
3. What are the bloc totals?
4. What does each poll say about individual parties?
5. What historical reliability context applies to the pollster?

### Overview panel

One strong analytics panel near the top:
- newest-update timestamp;
- cross-pollster bloc comparison;
- range / disagreement if useful;
- clear semantic legend.

### Pollster results

Each unit should show:
- pollster name;
- media outlet / publisher;
- poll date;
- bloc summary;
- party details;
- reliability context.

Do not render every piece of metadata as a badge.

Use borders, alignment, and typography before introducing chips.

---

## 11. Historical Comparison Screen

Treat this as a professional analytical table.

Header:
- short title;
- concise explanation;
- time-horizon slider directly connected to the result.

Slider:
- dark track;
- Spectral Cyan active track / thumb;
- clear selected day value;
- visible keyboard focus.

Comparison table priorities:
1. pollster identity;
2. expected error;
3. other accuracy metrics;
4. data support;
5. uncertainty.

Metric help popovers:
- `#263249` surface;
- Hairline border;
- 12px radius;
- white title;
- Fog Gray explanation;
- maximum readable width around 320px.

---

## 12. Methodology Screen

Do **not** present every methodology item as an isolated card.

Use an editorial documentation layout:

```text
Title
Intro

01  Main error metric
    explanation
    formula

02  Poll selection
    explanation
    formula
```

Use:
- numbered section markers;
- strong text hierarchy;
- divider lines;
- restrained formula surfaces;
- readable text width.

Formula blocks:

```css
background: #202A3E;
border: 1px solid #334056;
border-radius: 10px;
padding: 16px 20px;
direction: ltr;
```

Formula text:
- Bone White;
- cyan only for small key variables/highlights if useful;
- never use glowing syntax-color effects.

---

## 13. Navigation

Use a simple horizontal tab system.

Inactive:
- Fog Gray text;
- transparent background.

Active:
- Bone White text;
- subtle Tide Raised background or cyan underline;
- optional cyan icon / marker.

Recommended active treatment:

```css
background: #263249;
color: #ffffff;
border: 1px solid #3C4A62;
```

with a small cyan accent rather than a fully cyan tab.

On mobile, the tab row may horizontally scroll if necessary.

---

## 14. Buttons

PollTrust is not CTA-heavy. Bright buttons should be rare.

Primary:
- Tide Raised surface;
- Bone White text;
- Hairline border.

Use cyan for:
- focus ring;
- icon;
- border on emphasized action.

Secondary:
- transparent with border.

Icon buttons:
- 32–36px visual size;
- ideally 40px+ touch target.

Visible keyboard focus:

```css
outline: 2px solid #6AE4FF;
outline-offset: 2px;
```

---

## 15. Icons

Use one simple outline icon family.

Preferred:
- 1.5–2px stroke;
- rounded line caps;
- no filled decorative icons;
- 16–20px normal size;
- Spectral Cyan only for selected or important states.

Avoid using icons merely to decorate headings.

---

## 16. Motion

Motion should communicate state, not add spectacle.

Allowed:
- 120–180ms hover transitions;
- tab indicator transitions;
- accordion / detail expansion;
- subtle chart transitions.

Avoid:
- floating cards;
- glow pulses;
- continuous background movement;
- parallax;
- springy oversized motion.

Respect:

```css
@media (prefers-reduced-motion: reduce)
```

---

## 17. RTL Rules

PollTrust is natively RTL.

Required:
- `dir="rtl"` on the document;
- Hebrew copy aligned according to content hierarchy;
- sticky pollster table column sticks to `right: 0`;
- icon placement follows Hebrew reading order;
- numeric data may use LTR isolation when needed;
- formulas explicitly use `dir="ltr"`;
- dates and mixed Hebrew/English names must be inspected visually.

Use CSS logical properties where possible:

```css
margin-inline-start
margin-inline-end
padding-inline
border-inline-start
inset-inline-start
```

rather than hard-coding `left` and `right`, except where browser behavior requires an explicit RTL table workaround.

---

## 18. Responsive Rules

Validate at minimum:
- 390 × 844
- 768 × 1024
- 1440 × 900

### Mobile
- preserve comparison tasks;
- 16px page padding;
- reduce panel padding to 16–20px;
- stack summary groups where necessary;
- never shrink text below readability;
- allow analytical tables to scroll horizontally;
- keep pollster identity visible;
- avoid turning every data row into an oversized mobile card.

### Desktop
- max content width around 1200–1280px;
- use horizontal space for comparisons;
- avoid excessively wide prose;
- methodology text should remain around 700–800px readable line width even inside a wider page.

---

## 19. Accessibility

Target WCAG 2.2 AA.

Required:
- keyboard-operable tabs and popovers;
- visible focus states;
- sufficient contrast;
- no meaning by color alone;
- semantic tables;
- accessible names on info controls;
- 40px+ touch targets where practical;
- correct heading hierarchy;
- `aria-live` only where genuinely useful;
- reduced-motion support.

---

## 20. Do / Don't

### Do
- Use Pirsch-inspired analytics hierarchy: clear metrics, compact filters, bordered analytical surfaces, strong grouping.
- Use Idle Finance's deep navy + cyan color language.
- Keep the data visually stronger than the interface chrome.
- Use flat surfaces and hairline borders.
- Keep tables as proper tables.
- Use whitespace to separate analytical concepts.
- Keep cyan rare enough that it remains meaningful.
- Make Hebrew typography feel first-class.
- Let current-poll semantic bloc colors remain visible as data.
- Inspect the rendered site repeatedly at desktop and mobile widths.

### Don't
- Do not use Pirsch's cream/yellow/green palette.
- Do not copy Idle Finance's crypto/trading branding, giant hero text, or marketing gradients.
- Do not introduce glassmorphism.
- Do not use glowing cyan borders around every panel.
- Do not add shadows to cards.
- Do not use a gradient as a card fill.
- Do not make every element a rounded card.
- Do not overuse badges or pills.
- Do not convert analytical tables into visually inefficient card lists.
- Do not use cyan as a political category.
- Do not alter PollTrust's calculations or data semantics for visual simplicity.

---

## 21. Quick Token Reference

```css
:root {
  --color-bg: #17202E;
  --color-surface: #202A3E;
  --color-surface-raised: #263249;

  --color-accent: #6AE4FF;

  --color-text-primary: #FFFFFF;
  --color-text-secondary: #CDD0D6;
  --color-text-muted: #9098A6;

  --color-border: #334056;
  --color-border-strong: #0B1018;

  --color-bloc-change: #4F8CFF;
  --color-bloc-coalition: #FF627D;
  --color-bloc-neutral: #8B95A5;

  --font-ui: "Heebo", "Noto Sans Hebrew", "Arial Hebrew", Arial, sans-serif;

  --text-xs: 12px;
  --text-sm: 14px;
  --text-md: 16px;
  --text-lg: 20px;
  --text-xl: 28px;
  --text-2xl: 40px;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-pill: 999px;

  --page-max-width: 1280px;
  --content-reading-width: 760px;
}
```

---

## 22. Agent Implementation Instruction

When implementing PollTrust:

1. Read this file before editing frontend code.
2. Treat this file as the visual source of truth.
3. Preserve the existing functional/data behavior.
4. Inspect the current rendered site before changing it.
5. Establish the tokens first.
6. Redesign the overall hierarchy before polishing individual controls.
7. Use browser screenshots after every substantial pass.
8. Validate all three main views at 390px, 768px, and 1440px widths.
9. Perform at least one second-pass critique after the first redesign is visually complete.
10. Do not declare completion based on source code alone.

---

## Reference provenance

This design system intentionally combines:
- **Pirsch Analytics (Refero)** for analytics presentation patterns and structural hierarchy.
- **Idle Finance (Refero)** for palette, dark surfaces, cyan accent, and flat border-based elevation.

The result is a PollTrust-specific system rather than a direct copy of either source.
