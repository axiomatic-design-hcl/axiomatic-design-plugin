# Changelog

This file records changes to the marketplace and its plugin. Releases use a repository tag named `v<version>`.

## Unreleased

- Added `adhcl-scaffold` to lay out a source tree from a model, with an optional numbered FR/DP/PV layout.
- Added `ad_layout_check.py`. It builds code-reference matrices from the tree and compares them with the model's influence claims and `cells` defaults. A reference counts for its own cell and each ancestor cell.
- A code reference beside an authored zero is a review warning. Under `--expect`, it is an error. The skill takes the `--expect` policy from the model's classification.
- Made empty inventories, missing pairings, invalid paths, and unsupported model inputs fail instead of passing silently.
- The checker reads `coupling` blocks and `flow` loops. Several files can share one PV name, for example `pv1_x.h`, `pv1_x.c`, and `pv1_x.test.ts`. Files directly in the source root compose like `src/app/`.
- A structure-only scaffold throws the language's not-implemented error in each unimplemented body. New storage identifiers start with the owning DP folder name. Existing public names change only with approval.
- Added focused checker regression tests and skill evaluation cases.
- Added `examples/trailhead` with a model, an explanatory report, and an `adhcl diagram` page.

## 0.1.2 - 2026-11-24

- Added a Codex marketplace catalog and manifests for both plugins. Codex uses the same skills and references as Claude Code.
- Added Codex installation and usage instructions. The Claude Code hook and verifier agent do not run in Codex.
- Added an isolated Codex installation check to CI.

## 0.1.1 - 2026-11-18

The marketplace lists a second plugin, `adhcl`. Before this change, the `adhcl` skill was in the repository, but Claude Code could not install it.

The `adhcl` plugin contains these parts:

- The `adhcl` skill, moved to `plugins/adhcl/skills/adhcl/` with its references and evals.
- The `adhcl-verifier` subagent. It runs `adhcl validate` in a fresh context and does not edit files.
- A `PostToolUse` hook. It runs `adhcl validate` after Claude edits a RequirementsHCL file and gives error findings to Claude.

The tool guide of the skill now describes the commands and exit codes of adhcl 0.2.

A GitHub Actions workflow validates the marketplace and both plugins, and runs the tests for the hook.

## 0.1.0 - 2026-11-12

This release prepares the first Claude Code marketplace and plugin. The marketplace lists `axiomatic-design-skills` for installation.

The plugin contains one skill, `axiomatic-software-design`, and its reference files. The skill helps users design and review software systems with Axiomatic Design.

The README files provide installation commands for the GitHub repository. The plugin includes an Apache 2.0 license and an icon.
