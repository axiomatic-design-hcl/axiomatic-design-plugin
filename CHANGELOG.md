# Changelog

This file records changes to the marketplace and its plugin. Releases use a repository tag named `v<version>`.

## Unreleased

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
