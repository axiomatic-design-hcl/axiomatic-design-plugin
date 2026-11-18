# Tool use

The specification defines report operations but no executable interface.
The Go tool `adhcl` implements part of it.
Its source is the `axiomatic-design-hcl/adhcl` repository.
The name `adhcl` in a request does not establish that a compatible binary is installed.

## Discover the installed interface

Read the target repository's tool instructions before invoking an executable.
Find `adhcl` through the host's executable lookup or the repository's documented binary path.
On a POSIX host, executable lookup uses this command:

```sh
command -v adhcl
```

If a binary exists, read its version and its help:

```sh
adhcl version
adhcl --help
adhcl validate --help
```

Read relevant subcommand help before choosing flags or positional arguments.
Make sure that its supported language contract matches the target files.
Use only the command forms that its documentation or help establishes.
Do not invent version, input, profile, context, candidate, or output flags.

## Known interface of adhcl 0.2

The README of adhcl 0.2 documents these command forms:

```sh
adhcl version
adhcl validate [--profile source|architecture] [--candidate REF] [--context REF] [--] PATH
adhcl diagram [--profile source|architecture] [--candidate REF] [--context REF] [-o FILE|--output FILE] [--] PATH
```

Put options before the path and give exactly one path.
`--candidate` takes `decision.NAME.candidate.NAME`, and `--context` takes `context.NAME`.
`diagram` writes one self-contained HTML page and implements the `html` operation.
The `matrix`, `master`, `junctions`, `dsm`, `impact`, `evidence`, and `all` operations have no command in adhcl 0.2.

The exit codes of `validate` are:

1. `0`: validation completed without error findings.
2. `1`: an input, parse, assessment, required attachment, or output step failed.
3. `2`: the command line is invalid.

For `diagram`, exit code 0 means that the page was delivered, even when it shows error findings.
Use `validate` as the gate.
adhcl 0.2 reports every `terraform_binding` and `event_model_link` attachment as `unknown`, because it receives no observations or behavior models.
If the installed help differs from this section, follow the help and report the difference.

## When the tool is absent

If the binary is absent, finish the files and report that full language validation did not run.
Do not install an unrelated package named `adhcl`.
Do not restore the historical Python experiment as a substitute.
The experiment does not implement this contract.

## Select the input

Use a core file when the model occupies one file.
Use a core directory when the model occupies immediate `.ad.hcl` members of that directory.
Directory selection does not recurse or load a manifest implicitly.

Use the explicit `.ad.project.hcl` path when attachments belong to the assessment.
A manifest reads only its listed files and requires every declared owner.
A core-only run cannot establish attachment success.

Manifest paths are literal paths relative to the manifest directory.
Do not use globs, absolute paths, or paths that escape that directory.
List each physical file once.

## Select the operation

These names describe operations, not established command spellings.
Map them to the installed interface only after reading its help.
Do not present operation names alone as executable commands.
If the installed tool has no command for an operation, say that the report did not run.

The specification defines these operations:

1. Use `validate` for structural, profile, assertion, and evidence findings.
2. Use `matrix` for sibling influence matrices.
3. Use `master` for the leaf FR-to-DP matrix.
4. Use `junctions` for qualified module composition.
5. Use `dsm` for dependencies between leaf controls.
6. Use `impact` for definite effects and possible change obligations.
7. Use `evidence` for qualified probability and information bounds.
8. Use `html` for the self-contained design report.
9. Use `all` for all reports except DP-specific impact and HTML.

The `source` profile preserves specified completeness gaps as warnings.
The `architecture` profile requires operational criteria and complete architectural contracts.
Neither profile makes unsupported claims true.
Do not lower the profile to hide an error without explaining the change.

## Exercise and interpret

Run the documented validation operation against the exact selected input.
If the request includes a report, run that report for the same candidate, context, and profile.
Retain the actual command, exit status, findings, and output location.

Read `diagnostics.md` before interpreting process success.
An operation succeeds only when its required stages complete without applicable errors.
Warnings and qualified unknowns remain part of the result.

An unavailable required owner prevents complete project processing.
Unavailable observations can produce unknown binding results without proving implementation conformance.
A resolved behavior link establishes target identity, not satisfaction of an FR.
An assertion does not supply missing effects or evidence.

## Fallback when the language tool is unavailable

Use the native Go parser `github.com/hashicorp/hcl/v2/hclsyntax` if a parser harness is available.
Parse each authored core, manifest, and attachment file as native HCL.
Report parser diagnostics without relabeling them as typed language findings.

A parser accepts expressions that this language rejects.
Manually compare the files with the schema when full language validation is unavailable.
State that this comparison is not an implemented conformance test.

If Go or its parser dependency is unavailable, report that parsing also did not run.
Do not claim a successful parse from visual inspection.
Do not invent an executable or supported command workflow for this specification.
