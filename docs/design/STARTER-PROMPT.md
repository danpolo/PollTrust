# PollTrust UI/UX redesign — autonomous implementation task

Work directly on the existing PollTrust repository in this workspace.

This is an IMPLEMENTATION task, not a planning or code-generation task.

Do not respond by giving me code to copy.
Do not merely describe what should be changed.
Do not stop after proposing a design.

You must edit the actual repository files yourself, run the application, inspect the rendered result in the browser, iteratively improve it, test it, and only then finish.

## Source of truth

Read `DESIGN.md` in full before making design decisions.

`DESIGN.md` intentionally combines:
- Pirsch Analytics for analytics presentation, information hierarchy, metrics, tables, filters, spacing, and data-display patterns.
- Idle Finance for the color palette and dark surface language.

Treat `DESIGN.md` as the visual source of truth.

Also read:
- `README.md`
- `index.html`
- `assets/styles.css`
- `assets/app.js`
- relevant data files
- relevant tests
- `.agents/rules/polltrust-ui-guardrails.md`

Use these skills where relevant:
- `polltrust-ui-design`
- `frontend-design`
- `web-design-guidelines`
- `visual-qa`

## First inspect the current state

Before editing:

1. Inspect `git status` and the current working tree.
2. Preserve and evaluate any existing unfinished UI changes instead of blindly replacing them.
3. Inspect the currently deployed production site:
   `https://danpolo.github.io/PollTrust/`
4. Start the local site with:

   `python -m http.server 8000`

5. Open:
   `http://localhost:8000`

6. Capture baseline screenshots of the existing UI at approximately:
   - 390 × 844
   - 768 × 1024
   - 1440 × 900

7. Inspect all three main views:
   - current polls
   - historical comparison
   - methodology

Identify the most important visual hierarchy, readability, responsiveness, RTL, and usability problems before making changes.

## Implement the redesign

Apply the redesign directly to the repository.

Preserve:
- all PollTrust calculations;
- all data semantics;
- pollster identities and lineages;
- the discounted shared historical prior between Direct Polls / Zuriel Sharon and NEXT DATA / Shlomo Filber;
- current poll ingestion/data behavior;
- Hebrew user-facing text;
- correct RTL behavior.

Do not:
- turn PollTrust into a generic SaaS/admin dashboard;
- introduce political recommendations or persuasion;
- change calculations for visual convenience;
- migrate frameworks unless there is a compelling technical reason;
- paste proposed code into chat instead of applying it.

## Mandatory browser-driven iteration

The first implementation pass is NOT completion.

After every substantial visual pass:

1. Ensure the local server is running.
2. Use Antigravity's browser capabilities to inspect the actual rendered site at `http://localhost:8000`.
3. Test approximately:
   - 390 × 844
   - 768 × 1024
   - 1440 × 900
4. Inspect all three main views and important interactions.
5. Capture screenshots.
6. Critique the rendered result as a senior UI/UX designer.
7. Identify the highest-impact remaining problems.
8. Edit the actual files to fix them.
9. Reload and inspect again.

Repeat this loop until further changes would be minor polish rather than substantial improvements.

Do not infer visual quality only from HTML/CSS source.

Pay particular attention to:
- Hebrew typography;
- RTL directionality;
- current-poll information hierarchy;
- analytics presentation;
- bloc visualization;
- historical table readability;
- sticky pollster column on narrow screens;
- metric info popovers;
- slider interaction;
- formula rendering;
- spacing rhythm;
- data density;
- mobile behavior;
- keyboard accessibility;
- contrast;
- excessive cards, pills, borders, or decorative UI.

## Validation

Before completion:

- run the relevant automated tests;
- check the browser console for errors;
- verify there is no unintended horizontal viewport overflow;
- verify all three main views work on mobile and desktop;
- verify important keyboard interactions;
- compare final screenshots against the baseline.

## GitHub and deployment

Do not push intermediate or broken design states.

Only after the local redesign has been fully validated:

1. review `git diff`;
2. make sure only intended project changes are included;
3. commit the completed redesign;
4. push it to the PollTrust GitHub repository;
5. wait for / verify the GitHub Pages deployment;
6. open `https://danpolo.github.io/PollTrust/`;
7. verify that the deployed version matches the locally validated version.

If deployment reveals a problem, fix it, validate locally again, push the correction, and verify deployment again.

## Completion artifact

Do not finish with only a textual summary.

When the implementation is complete, provide screenshot artifacts that I can visually review and comment on.

At minimum provide:
- final desktop screenshot;
- final mobile screenshot;
- preferably screenshots of each of the three major views where useful.

Then give a concise summary of:
- the major design decisions;
- files changed;
- tests run;
- browser/interaction checks performed;
- Git commit/push/deployment status;
- any remaining limitations.

The task is complete only when the actual repository has been updated, the UI has been iteratively browser-tested, the final deployment has been verified, and the screenshot artifacts have been produced.