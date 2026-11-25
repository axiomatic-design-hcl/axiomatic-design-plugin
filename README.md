# Axiomatic Design marketplace

This marketplace provides two plugins for Codex and Claude Code, for software architects and developers.

| Plugin | What it does |
| --- | --- |
| `axiomatic-design-skills` | Helps you design or review a system with Axiomatic Design. |
| `adhcl` | Writes the design as RequirementsHCL `.ad.hcl` files and checks them with the `adhcl` tool. Lays out a source tree from a model and rebuilds the design matrices from that tree. |

See [examples/trailhead](examples/trailhead/) for an uncoupled model of an offline hiking app: the `.ad.hcl` file, a report with diagrams, and the `adhcl diagram` page.

## Install in Codex

Install Codex CLI 0.172.0 or newer. Register the marketplace from GitHub:

```bash
codex plugin marketplace add axiomatic-design-hcl/axiomatic-design-plugin
```

Install both plugins and list them:

```bash
codex plugin add axiomatic-design-skills@axiomatic-design-marketplace
codex plugin add adhcl@axiomatic-design-marketplace
codex plugin list --marketplace axiomatic-design-marketplace
```

For a local checkout, register the marketplace from the repository root instead:

```bash
codex plugin marketplace add .
```

Start a new Codex chat after installation. Use `$axiomatic-software-design` for design work, `$adhcl` to write or check `.ad.hcl` files, and `$adhcl-scaffold` to lay out a source tree from a model. Both plugins share their skills and references with Claude Code.

Codex loads the portable `plugin.json` in each plugin directory. The repository catalog is `.agents/plugins/marketplace.json`; its paths resolve from the repository root. See [OpenAI’s plugin packaging guide](https://developers.openai.com/plugins/build/plugins) for the format.

The Codex ADHCL plugin includes the authoring skill and the scaffold skill. Its manifest disables automatic hook discovery: the bundled `PostToolUse` hook and `adhcl-verifier` agent are Claude Code components. In Codex, the skills run the available `adhcl` tool and report when full validation cannot run. Install the binary from the [adhcl repository](https://github.com/axiomatic-design-hcl/adhcl).

## Install in Claude Code

Install [Claude Code](https://code.claude.com/docs/en/setup) first. Open your shell. Register the marketplace from GitHub:

```bash
claude plugin marketplace add axiomatic-design-hcl/axiomatic-design-plugin
```

Install the plugins:

```bash
claude plugin install axiomatic-design-skills@axiomatic-design-marketplace
claude plugin install adhcl@axiomatic-design-marketplace
```

Restart Claude Code after installation. Run `claude plugin list` to make sure that the plugins are enabled.

The `adhcl` plugin runs the `adhcl` binary when it is on your `PATH`. Get the binary from the [adhcl repository](https://github.com/axiomatic-design-hcl/adhcl).

## Use in Claude Code

Start Claude Code and enter `/axiomatic-design-skills:axiomatic-software-design`. Describe the system, its requirements, and the design decision. The skill maps requirements to design choices, examines how choices affect requirements, and reports uncertainty.

To write the result as files, enter `/adhcl:adhcl` or ask Claude to write the design as `.ad.hcl`. To lay out a source tree from the model, enter `/adhcl:adhcl-scaffold`. Claude can select each skill from your request.

See the [axiomatic-design-skills README](plugins/axiomatic-design-skills/README.md) and the [adhcl README](plugins/adhcl/README.md) for scope and data details.

## Update and contribute

For a local checkout, pull the repository changes. In Codex, run the two `codex plugin add` commands again to refresh the cached plugins, then start a new chat. In Claude Code, restart the client. See [CONTRIBUTING.md](CONTRIBUTING.md) for validation and release instructions. The repository uses the [Apache License 2.0](LICENSE).
