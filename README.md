# Axiomatic Design marketplace

This marketplace provides two Claude Code plugins for software architects and developers. A marketplace is a catalog of plugins that Claude Code can install.

| Plugin | What it does |
| --- | --- |
| `axiomatic-design-skills` | Helps you design or review a system with Axiomatic Design. |
| `adhcl` | Writes the design as RequirementsHCL `.ad.hcl` files, and validates them with the `adhcl` tool after each edit. |

## Install

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

## Use

Start Claude Code and enter `/axiomatic-design-skills:axiomatic-software-design`. Describe the system, its requirements, and the design decision. The skill maps requirements to design choices, examines how choices affect requirements, and reports uncertainty.

To write the result as files, enter `/adhcl:adhcl` or ask Claude to write the design as `.ad.hcl`. Claude can select each skill from your request.

See the [axiomatic-design-skills README](plugins/axiomatic-design-skills/README.md) and the [adhcl README](plugins/adhcl/README.md) for scope and data details.

## Update and contribute

For a local checkout, pull the repository changes and restart Claude Code. See [CONTRIBUTING.md](CONTRIBUTING.md) for validation and release instructions. The repository uses the [Apache License 2.0](LICENSE).
