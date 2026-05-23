---
description: "Review BUILD repo changes (Gate 1) + distribute to templates with variant overlays (Gate 2)"
---

Sync CO/COC artifacts. Behavior depends on repo type (from `.claude/VERSION`).

Detailed protocol: `skills/30-claude-code-patterns/sync-flow.md` (loaded by sync-reviewer + coc-sync agents).

**Usage**: `/sync [target]`

- At loom/ (coc-source): `target` = `py`, `rs`, `rb`, `base`, or `all`. If omitted, ask.
- At downstream projects (coc-project): no target needed.

## Step 0: Detect Repo Type

Read `.claude/VERSION` → `type` field:

- `coc-source` → Gate 1 + Gate 2 (below)
- `coc-project` → Downstream Sync (delegate to `skills/30-claude-code-patterns/sync-flow.md` § Downstream Sync)
- `coc-use-template` / `coc-build` → **MUST verify** the repo is the actual template/BUILD repo before routing to loom. Check `basename $(pwd)` + `git remote get-url origin` (normalize SSH `git@host:owner/repo.git` → `owner/repo`) against known repos: `kailash-coc-claude-{py,rs,rb,prism}`, `kailash-{py,rs,prism}`. If match → "receives artifacts from loom/, run `/sync` at loom/". If no match → treat as `coc-project` and auto-correct VERSION in-place (type → `coc-project`, upstream → `{template, template_repo, template_version, synced_at, sdk_packages}` per `.claude/hooks/lib/version-utils.js::correctTemplateDerivedVersion`), then Downstream Sync.
- Missing → ask user what type this repo is

## Two Gates (coc-source — loom/ only)

This command has two sequential gates. Gate 1 runs automatically if unreviewed changes exist. Detailed protocol for each gate is in `skills/30-claude-code-patterns/sync-flow.md` § Gate 1 / § Gate 2 — the agents below load that skill at delegation time.

### Gate 1: Review (inbound — BUILD repo → loom/)

Scans the BUILD repo for artifact changes not yet upstreamed to loom/.

**Trigger**: Runs automatically when `/sync` detects unreviewed changes. Also runs if the user explicitly says "review" (e.g., `/sync py review`).

**Process summary** (full protocol in skill):

1. Read `sync-manifest.yaml` for tier membership + variant mappings; read BUILD repo path from `repos.{target}.build`.
2. Read SDK version from BUILD repo's `pyproject.toml` (py) / `Cargo.toml` (rs) — report in review header.
3. Compute expected state (loom + variant overlay), diff BUILD repo's `.claude/` against it.
4. Check `.claude/.proposals/latest.yaml` status (`pending_review` / `reviewed` / `distributed`); for `reviewed`, re-review only entries appended after `reviewed_date`.
5. For each NEW or MODIFIED file, classify (sync-reviewer agent: global vs variant vs skip).
6. Place files: global → `.claude/{type}/{file}`, variant → `.claude/variants/{lang}/{type}/{file}`, skip → leave in BUILD only.
7. Mark proposal as reviewed.

**Skip when**: No diff between BUILD and expected state, or user says "distribute only" / "skip review".

### Gate 2: Distribute (outbound — loom/ → templates)

Merges loom/ source + variant overlays into USE template repos. This is a **merge** — templates may have legitimate local content.

**Process summary** (full protocol in skill):

1. Read manifest for tiers, variants, exclusions (`exclude:`, `use_exclude:`).
2. Inventory template state.
3. Compute expected state for the target — read `repos.<target>.tier_subscriptions` (REQUIRED in v2.21.0+; missing = manifest defect, halt sync), emit only files matched by subscribed tier patterns. Apply `use_exclude:` (BUILD-only paths). MUST include tier-independent runtime infra: `.claude/hooks/**`, `.claude/bin/**`, `.claude/.coc-obsoleted`. Apply variant overlay from `variants/{repos.<target>.variant}/`. Top-level files declared in `variant_only:`.
4. Per-file merge decisions: UNCHANGED skip, NEW add, MODIFIED flag if template has USE-specific adaptations, TEMPLATE-ONLY preserve.
5. Present merge plan (no bulk "Apply all").
6. Apply approved changes.
7. Update `.coc-sync-marker` with timestamp + file list.
8. Update `.claude/VERSION` — `upstream.build_version`, `upstream.sdk_packages` from BUILD `pyproject.toml`/`Cargo.toml`.
9. Update SDK dependency pins in target's `pyproject.toml` / `Cargo.toml` — MANDATORY.
10. Install updated dependencies — `uv sync` (py) / `cargo check` (rs) — MANDATORY.
11. Verify hooks — every entry in `settings.json` has a script on disk.
12. Mark BUILD proposal as `distributed` with `distributed_date`.

**Multi-CLI scaffold (Step 4.6 in coc-sync)**: for multi-CLI USE templates (`template_type: multi-cli`), Gate 2 emits the symlinks and conditional manifest declared under `sync-manifest.yaml::multi_cli_overlays.<template_type>.symlinks` + `manifest_distribute`. Closes the `/migrate` Step-4a inline-workaround gap (#184). Cc-only-legacy templates are unaffected.

**Pre-commit gate**: run `tools/verify-overlays.sh <target>` from loom — MUST report `Failing: 0` (slot-keyed-aware since v2.21.1). Any CRIT-2 / drift / deployed-missing row blocks the cycle.

**Report shape**:

```
## Sync Report: loom/ → kailash-coc-claude-py/
Gate 1: 3 reviewed (1 global, 1 variant-py, 1 skipped), SDK 2.2.1
Gate 2: 12 updated, 2 added, 1 flagged, 482 unchanged, 3 preserved
SDK pins: kailash 2.2.1→2.3.0, kailash-dataflow 1.2.1→1.3.0
Dependencies: uv sync ✓ | Hooks: 11/11 | VERSION: 1.0.0→1.1.0
```

## Exclusions

Never synced: `learning/`, `.proposals/`, `variants/`, `settings.local.json`, `CLAUDE.md`, `.env`, `.git/`. `sync-manifest.yaml` is excluded from cc-only-legacy templates AND from BUILD repos, but **emitted to multi-CLI USE templates** when `multi_cli_overlays.<template_type>.manifest_distribute: true` (the emitter at the project repo reads it at `/migrate` time). Full list: `skills/30-claude-code-patterns/sync-flow.md` § Exclusions.

## Delegate

- **Gate 1** → **sync-reviewer** agent
- **Gate 2** → **coc-sync** agent (MUST read target content before writing; no bulk overwrites)
- **Downstream** → no delegation (in-place per skill protocol)

## Examples

- `/sync py` — loom/: review kailash-py changes, merge to coc-claude-py + coc-py
- `/sync rs` — loom/: review kailash-rs changes, merge to coc-claude-rs + coc-rs
- `/sync rb` — loom/: distribute to coc-claude-rb (no BUILD)
- `/sync` — downstream project: pull latest from USE template
