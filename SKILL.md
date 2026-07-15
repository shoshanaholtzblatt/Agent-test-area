---
name: usability-path-analysis
description: Analyze audio-stripped screen-share recordings from usability studies to reconstruct participant navigation paths. Use this skill whenever the user wants to extract path data, screen flows, navigation sequences, task timelines, or behavioral analysis from usability session videos or screen recordings — including when they mention "path analysis," "screen flow," "where participants went," "usability video analysis," "session recordings," or ask to compare participant navigation across sessions. Also use when the user wants to extract frames from a usability video, classify screens, or measure dwell time and backtracking.
---

# Usability Path Analysis

Reconstruct participant navigation paths from screen-share recordings. The core insight: this is a **classification problem, not a description problem**. Each extracted frame gets matched against a known screen inventory; deterministic code then assembles the path, computes dwell times, and detects deviations. Claude does visual recognition; scripts do sequence math.

## Pipeline overview

```
transcript ──► task windows ──► frame extraction ──► frame classification ──► path assembly ──► deliverables
 (parse)        (timestamps)     (change detection)   (Claude vision vs.       (deterministic     (per-session JSON +
                                                       screen inventory)        script)            cross-session report)
```

Run the stages in order. Each stage's output feeds the next as files on disk, so a failed stage can be re-run without repeating earlier work.

## Stage 0: Screen inventory (one-time per study)

The screen inventory is the reference set every frame is classified against. Without it, classification degrades into freeform description and paths become unreliable. **Do not skip this stage.** If no inventory exists yet, read `references/screen-inventory.md` and build one with the user before touching video.

Three supported sources (ask the user which fits, or detect from what's available):

1. **Figma MCP** — export screens from the prototype file; node names become screen IDs. Best when testing a Figma prototype (1:1 visual match). If a Figma MCP tool is connected, offer this first.
2. **Manual screenshots** — user supplies labeled captures of each screen. Best for production software.
3. **Bootstrap from video frames** — extract frames from one session, cluster visually distinct screens, have the user name them. Best when nothing else exists; guarantees zero domain gap between references and captures.

Hybrid is encouraged: Figma for screen names and the expected-path graph, real captured frames for the visual references (Figma renders are clean and high-contrast; video frames are compressed — the domain gap can hurt matching).

The inventory lives in `screen-inventory/` in the working directory:

```
screen-inventory/
├── inventory.json        # screen IDs, names, distinguishing features, expected transitions
└── refs/
    ├── home.png
    ├── transfer-amount.png
    └── ...
```

See `references/screen-inventory.md` for the inventory.json schema, the bootstrap-from-video procedure, and how to encode the expected path graph (from Figma prototype connections or the user's task design).

## Stage 1: Parse the transcript into task windows

Transcripts include timestamps and moderator/participant speaker labels. Use the moderator's utterances to locate task boundaries — task prompts ("Okay, now I'd like you to try to...") open a window; wrap-up or next-prompt utterances close it.

Produce `task_windows.json`:

```json
{
  "session_id": "P07",
  "windows": [
    {
      "task_id": "task-1",
      "task_prompt": "Transfer $50 to your savings account",
      "start_s": 312.4,
      "end_s": 498.0,
      "transcript_excerpt": "MODERATOR: Okay, for this next one..."
    }
  ]
}
```

Show the windows to the user for confirmation before extracting frames — a misplaced boundary wastes an entire extraction pass. Keep the `transcript_excerpt`: it gets passed alongside frames during classification so the intended task disambiguates the flow.

## Stage 2: Extract frames

Run `scripts/extract_frames.py`. Screen shares are mostly static, so it does change detection: it samples small thumbnails at a base rate, computes RGB frame differences in Python, and grabs full-resolution PNGs only at the timestamps where content changed. Runs of no-change become dwell-time signal instead of duplicate images. (Change detection is done in Python rather than ffmpeg's `scene` filter deliberately — that filter can score some real transitions at zero and drop them silently.)

```bash
python3 scripts/extract_frames.py VIDEO.mp4 \
  --windows task_windows.json \
  --out frames/ \
  --sample-fps 2.0 --threshold 2.0
```

Key behaviors (see `--help` for all options):
- **Timestamps preserved**: every frame is named `<task_id>_t<seconds>.png` and logged to `frames/manifest.json`. Timestamps are the raw material for dwell-time math — never discard them.
- **PNG at native resolution**: thumbnails are only used for diffing; kept frames are full-resolution PNGs. JPEG artifacts and downscaling destroy UI text legibility, which is what classification rides on.
- **Bookend frames**: the first and last sample of every window are always captured regardless of change, so a window that opens mid-screen still has a starting state.
- **`--mode fps`**: keep every sample (fixed rate) — useful for threshold experiments and hand-validation passes.

Two tuning knobs, independently adjustable:
- **`--sample-fps`** (default 2.0) — temporal resolution: how often the screen is checked. Raise (4–8) for fast interactions or short-lived states; lower (0.5–1) for slow deliberate flows and smaller frame budgets.
- **`--threshold`** (default 2.0, mean absolute RGB difference on a 0–255 scale) — sensitivity: what counts as a change. Lower (0.5–1) catches partial page updates and small state changes; raise (4–8) if cursor blinks, video noise, or animated content flood the manifest.

If the manifest shows very few frames for a window where the transcript says the participant clearly navigated, lower the threshold first, then raise sample-fps. Treat both settings as an eval question, not constants (see Validation and tuning).

## Stage 3: Classify frames

Classify each window's frames **in timestamp order, in batches**, against the screen inventory. Read `references/classification.md` before the first classification pass — it contains the exact prompt structure, batching guidance, and the output schema. The essentials:

- Load the inventory reference images once per session; present frames with their timestamps.
- Include the window's `task_prompt` and `transcript_excerpt` so the intended flow is known.
- For each frame emit: `timestamp`, `screen_id`, `evidence` (what visible elements support the match), `confidence` (high/medium/low), and optional `state_notes` (modal open, error banner, form partially filled).
- **`unknown` and `transitional` are first-class labels.** Never force-fit an ambiguous frame to the nearest inventory screen — a confident wrong label corrupts the whole path, while `unknown` just flags a gap for human review.
- Infer actions from state changes ("modal appeared between t=340 and t=342"), not from cursor position — cursors are frequently illegible in compressed captures.

Save results to `classifications/<session>_<task>.json`.

## Stage 4: Assemble paths

Run `scripts/assemble_path.py`. This is deterministic — no LLM judgment — so results are auditable and re-runnable:

```bash
python3 scripts/assemble_path.py \
  classifications/P07_task-1.json \
  --inventory screen-inventory/inventory.json \
  --out paths/P07_task-1.json
```

It collapses consecutive same-screen frames into visits, computes dwell time per visit, detects revisits and backtracks, and — if the inventory contains an `expected_paths` graph — flags every off-path transition. Output includes both the machine-readable path and a human-readable timeline (`--timeline` writes a Markdown version).

Low-confidence and `unknown` segments are carried through, never silently dropped: the path JSON marks them and the timeline renders them as gaps to review.

## Stage 5: Deliverables

Two outputs per analysis run, both defined in `references/outputs.md`:

1. **Per-session path data** — the `paths/*.json` files plus a Markdown timeline per session/task: visit sequence, dwell times, backtracks, deviations, unknown gaps, notable state changes.
2. **Cross-session comparison report** — after multiple sessions are assembled, run `scripts/assemble_path.py --aggregate paths/ --out report/` to compute per-task aggregates (path variants and their frequencies, common deviation points, dwell-time outliers), then write the report following the structure in `references/outputs.md`. Keep interpretation grounded: the report states what the paths show; behavioral *why* claims stay tied to transcript evidence or are framed as open questions for the researcher.

## Validation and tuning

Before trusting the pipeline on a full study, validate on 1–2 sessions:
1. Hand-code the true path for those sessions (or have the researcher do it).
2. Run the pipeline at 2–3 extraction settings (vary threshold first, then sample-fps).
3. Compare transition sequences: missed transitions, phantom transitions, misclassified screens.
4. Pick the threshold/batching configuration with the best transition accuracy, and record it in the working directory's `config.json` so subsequent sessions use the same settings.

If classification accuracy is the bottleneck rather than extraction, the usual fixes in order of impact: rebuild visual references from captured frames instead of Figma exports; add distinguishing-feature text to `inventory.json`; reduce batch size; crop to the changed region for dense screens.

## What this skill does not do

- Cursor/click tracking (unreliable from compressed frames — inferred from state changes instead)
- Eye tracking or attention inference
- Sentiment or emotion analysis (video is audio-stripped; the transcript exists but behavioral claims beyond navigation stay out of scope)
- Task success judgment without researcher-defined success criteria — if the user wants success rates, ask them to define the end-state screen(s) per task first
