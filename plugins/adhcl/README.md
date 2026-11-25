# ADHCL

This plugin helps Codex and Claude Code write and check RequirementsHCL files. These files use the extensions `.ad.hcl`, `.ad.ext.hcl`, and `.ad.project.hcl`. It also turns a model into a source tree that repeats the model's IDs. Both clients use the same two skills. Claude Code also uses one subagent and one hook.

## Parts

| Part | Name | What it does |
| --- | --- | --- |
| Skill | `adhcl` | Turns a finished Axiomatic Design into `.ad.hcl` files, manifests, and attachments. It also repairs and reviews these files. |
| Skill | `adhcl-scaffold` | Turns an `.ad.hcl` model into a source tree with `src/dp<N>_<label>/`, `pv<N>_<label>`, and `tests/fr<N>_<label>/` items. Its bundled `ad_layout_check.py` rebuilds the design matrices from that tree and compares them with the model. |
| Subagent | `adhcl-verifier` | Runs `adhcl validate` in a fresh context and reports `PASS`, `FAIL`, or `NOT CHECKED`. It does not edit files. |
| Hook | `PostToolUse` | Runs `adhcl validate` after Claude edits a RequirementsHCL file, and shows error findings to Claude. |

The `adhcl` skill writes the design. It does not make design decisions. For design decisions, install the `axiomatic-design-skills` plugin from the same marketplace.

The layout checker needs Python 3.9 or later and no packages. A cross-folder reference in the code is evidence of a material influence; no reference does not prove that an influence is absent. See [the layout contract](skills/adhcl-scaffold/references/layout-contract.md).

## Install in Codex

Follow the [Codex installation instructions](../../README.md#install-in-codex). Start a new chat and enter `$adhcl` to write a model, or `$adhcl-scaffold` to lay out a source tree from a model.

Codex loads the skills and their references from `plugin.json`. The Claude Code hook and verifier agent do not run in Codex.
The skills run validation with the `adhcl` binary when it is available. They report when full validation cannot run.
Install the binary from the [adhcl repository](https://github.com/axiomatic-design-hcl/adhcl).

## Install in Claude Code

Install Claude Code first. Then run these commands in your shell:

```bash
claude plugin marketplace add axiomatic-design-hcl/axiomatic-design-plugin
claude plugin install adhcl@axiomatic-design-marketplace
```

Restart Claude Code after installation. Enter `/adhcl:adhcl` and give Claude the design to write, or enter `/adhcl:adhcl-scaffold` and name the model to lay out as a source tree. Claude can also select a skill from your request.

The hook and the subagent need the `adhcl` binary on your `PATH`. Build it from the [adhcl repository](https://github.com/axiomatic-design-hcl/adhcl) or download a release. Without the binary, the hook does nothing, and the subagent reports `NOT CHECKED`.

## How the Claude Code hook selects the input

After Claude edits or writes a file, the hook selects the input for `adhcl validate` in this order:

1. If the file is a `.ad.project.hcl` manifest, the hook validates that manifest.
2. If a manifest in the directory of the file, or in a parent directory up to the project directory, lists the file, the hook validates that manifest.
3. If the file is a core `.ad.hcl` file, the hook validates its directory. adhcl merges the `*.ad.hcl` files of a directory into one model.
4. If the file is a `.ad.ext.hcl` attachment that no manifest lists, the hook does nothing.

The hook ignores all other files. It uses `jq` when it is available.

If adhcl reports error findings (exit code 1), the hook gives the report to Claude, and Claude can repair the files. If adhcl rejects the command line (exit code 2), the hook shows a message to you. Warnings do not stop Claude.

## Configuration of the hook

Set these environment variables in your shell, or in the `env` object of a Claude Code settings file:

| Variable | Value | Effect |
| --- | --- | --- |
| `ADHCL_PROFILE` | `source` or `architecture` | Selects the adhcl profile. Without it, adhcl uses `source`. |
| `ADHCL_BIN` | A path | Uses this binary in place of `adhcl` on the `PATH`. |
| `ADHCL_HOOK_DISABLE` | `1` | Turns the hook off. |

The hook is a Bash script. On Windows, it runs only where Claude Code runs hooks through a Bash shell, for example Git Bash or WSL.

## Data

The skill and the subagent contain instructions and reference files. The hook runs the local `adhcl` binary on your files. The plugin sends no data to an external service. Your chosen client handles your prompts and any files that you ask it to read under its own service and privacy terms.

The bundled references in `skills/adhcl/references/`, except `authoring.md` and `tool-usage.md`, are copies of the RequirementsHCL specification. The plugin uses the [Apache License 2.0](LICENSE).
