# Axiomatic Design marketplace

This marketplace provides a Claude Code plugin for software architects and developers. The plugin helps you design or review a system with Axiomatic Design. A marketplace is a catalog of plugins that Claude Code can install.

## Install

Install [Claude Code](https://code.claude.com/docs/en/setup) first. Open your shell. Register the marketplace from GitHub:

```bash
claude plugin marketplace add axiomatic-design-hcl/axiomatic-design-plugin
```

Install the plugin:

```bash
claude plugin install axiomatic-design-skills@axiomatic-design-marketplace
```

Restart Claude Code after installation. Run `claude plugin list` to make sure that the plugin is enabled. Run `claude plugin details axiomatic-design-skills` to see its skill.

## Use

Start Claude Code and enter `/axiomatic-design-skills:axiomatic-software-design`. Describe the system, its requirements, and the design decision. You can also ask Claude to apply Axiomatic Design to a system. Claude can select the skill from your request.

The skill maps requirements to design choices, examines how choices affect requirements, and reports uncertainty. It does not require an external service. See the [plugin README](plugins/axiomatic-design-skills/README.md) for scope and data details.

## Update and contribute

For a local checkout, pull the repository changes and restart Claude Code. See [CONTRIBUTING.md](CONTRIBUTING.md) for validation and release instructions. The repository uses the [Apache License 2.0](LICENSE).
