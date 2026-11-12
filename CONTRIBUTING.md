# Contributing

This repository contains one Claude Code marketplace and one plugin. The plugin contains the `axiomatic-software-design` skill. Keep its reference files inside the skill directory so that Claude Code can load them with the plugin.

## Validate changes

Install [Claude Code](https://code.claude.com/docs/en/setup) first. Open a shell at the repository root. Run the marketplace validation:

```bash
claude plugin validate .
```

Run the plugin validation:

```bash
claude plugin validate ./plugins/axiomatic-design-skills
```

Start Claude Code with the local plugin:

```bash
claude --plugin-dir ./plugins/axiomatic-design-skills
```

In that session, enter `/axiomatic-design-skills:axiomatic-software-design` with a design question. Make sure that Claude can use the skill and its references. For installation changes, also follow the installation steps in [README.md](README.md).

## Release

Update the version in `plugins/axiomatic-design-skills/.claude-plugin/plugin.json` for a release. Record the changes in [CHANGELOG.md](CHANGELOG.md). Create a repository tag named `v<version>` after the release is ready. Users of a local checkout must pull the changes and restart Claude Code.
