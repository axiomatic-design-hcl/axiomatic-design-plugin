# Contributing

This repository contains Codex and Claude Code marketplace catalogs and two plugins:

- `plugins/axiomatic-design-skills` contains the `axiomatic-software-design` skill.
- `plugins/adhcl` contains the `adhcl` skill, the `adhcl-verifier` subagent, and a hook that runs `adhcl validate`.

Keep the reference files of each skill inside its skill directory so that both clients can load them with the plugin. Codex uses each plugin’s root `plugin.json` and the `.agents/plugins/marketplace.json` catalog. Claude Code uses the existing `.claude-plugin/` manifests and catalog. Keep plugin names, versions, and source paths consistent across the two formats. Codex manifests explicitly disable hook discovery so the Claude Code hook is not loaded there.

## Validate changes

Install Codex CLI 0.172.0 or newer and run the isolated installation check:

```bash
bash tests/test-codex-plugins.sh
```

It registers this checkout in a temporary `CODEX_HOME`, installs both plugins, and checks that their skills and references reach the installed cache. It does not change your Codex settings.

Install [Claude Code](https://code.claude.com/docs/en/setup) first. Open a shell at the repository root. Run the marketplace validation:

```bash
claude plugin validate .
```

Run the plugin validations:

```bash
claude plugin validate ./plugins/axiomatic-design-skills
claude plugin validate ./plugins/adhcl
```

Run the tests for the hook. They use a fake `adhcl` and need only Bash:

```bash
bash tests/test-validate-hook.sh
```

The `validate` workflow in `.github/workflows/` runs these commands for each pull request.

Start Claude Code with a local plugin:

```bash
claude --plugin-dir ./plugins/axiomatic-design-skills
claude --plugin-dir ./plugins/adhcl
```

In that session, use the skill with a design question or a design to write. Make sure that Claude can use the skill and its references. For the `adhcl` plugin, edit a `.ad.hcl` file and make sure that the hook reports adhcl errors. For installation changes, also follow the installation steps in [README.md](README.md).

The files in `plugins/adhcl/skills/adhcl/references/` other than `authoring.md` and `tool-usage.md` are copies of the `spec` repository. Update them together with the specification, and do not edit them here alone.

## Release

Update the version in both `plugin.json` and `.claude-plugin/plugin.json` of each changed plugin. Record the changes in [CHANGELOG.md](CHANGELOG.md). Create a repository tag named `v<version>` after the release is ready. Users of a local checkout must pull the changes. Codex users must rerun `codex plugin add` for the changed plugins and start a new chat; Claude Code users must restart the client.
