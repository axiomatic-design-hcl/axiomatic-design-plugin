# Axiomatic Design Skills

This plugin helps software architects and developers design or review systems with Axiomatic Design. It contains one skill, `axiomatic-software-design`. The skill maps requirements to design choices and examines their effects on one another. It also compares alternatives when evidence supports the comparison.

## Use the skill

Install Claude Code first. Register the marketplace from GitHub in your shell:

```bash
claude plugin marketplace add axiomatic-design-hcl/axiomatic-design-plugin
claude plugin install axiomatic-design-skills@axiomatic-design-marketplace
```

Restart Claude Code after installation. Enter `/axiomatic-design-skills:axiomatic-software-design` and describe your system and decision.

Give Claude your requirements, constraints, and available architecture evidence. The skill identifies assumptions and unknowns. It does not prove that a design is correct, and it does not replace testing.

## Data and sources

The plugin contains instructions and reference files. It has no connector, hook, or script that sends data to an external service. Claude Code handles your prompts and any files that you ask it to read under its own service and privacy terms.

The skill adapts a 1991 paper by Sun-Jae Kim, Nam P. Suh, and Sang-Gook Kim. See [source notes](skills/axiomatic-software-design/references/source-notes.md) for the citation and differences from the paper. The plugin uses the [Apache License 2.0](LICENSE).
