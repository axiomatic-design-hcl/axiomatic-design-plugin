---
name: adhcl-scaffold
description: "Lay out or review an app's source tree from a RequirementsHCL .ad.hcl model, with folder names that repeat the model's IDs: src/dp<N>_<label>/, pv<N>_<label>, and tests/fr<N>_<label>/. Use to scaffold an app from an axiomatic design, to map FRs, DPs, and PVs to code, or to make sure in CI that the code does not contradict the design matrix. The bundled checker builds code-reference matrices from the tree and compares them with the model's influence claims. For .ad.hcl syntax use adhcl. For design decisions use axiomatic-software-design."
---

# Build and check a source tree from an `.ad.hcl` model

This skill turns a model into a source tree and compares the tree with the model.
A functional requirement (FR) states an outcome.
A design parameter (DP) controls an outcome.
A process variable (PV) realizes a DP.
An influence record states whether a change to a DP affects an FR.

In the numbered layout, each folder name repeats a model ID, for example `dp2_1_sampling_policy`.
Code that uses another DP must spell that folder name.
The bundled checker finds these names and builds a code-reference matrix.
A code-reference matrix has FR rows and DP columns, like a design matrix.
Each `R` cell shows code in one DP branch that names a DP in another branch.

An `R` cell is a possible influence that the model must explain.
An `R` cell beside an authored zero shows a contradiction between code and design.
An empty cell does not prove a zero.
Shared state, resources, data, and configuration do not show in folder names.
Thus the checker can refute an independence claim, but it cannot prove one.
The justified zeros in the model remain the argument for independence.

The model is the input.
Do not redesign the system to fit the layout.
Use `axiomatic-software-design` for design decisions.
Use `adhcl` to change `.ad.hcl` files.

## 1. Read the inputs

1. Read [the layout contract](references/layout-contract.md) before you create or review a path.
2. Read [the adhcl tool guide](../adhcl/references/tool-usage.md) before you run `adhcl`.
3. Read [the adhcl schema](../adhcl/references/schema.md) when you need the meaning of a model field.
4. Identify the exact model input: one core `.ad.hcl` file, one core directory, or one `.ad.project.hcl` manifest.
5. Record the candidate, context, and profile that the user requests.
6. Inspect the target repository: language, build tool, test framework, and source roots.
7. If a new project has no language, ask the user for one.
8. Record whether the user wants structure only or working behavior.

The `adhcl` profile (`source` or `architecture`) selects the strictness of model validation.
A candidate selects a design alternative. A context names operating conditions.

## 2. Validate the model and find its classification

1. Run `adhcl validate` on the exact input, as the tool guide describes.
2. Record the command, the exit code, and the findings.
3. If `adhcl` is absent, report that full model validation did not run. Continue with layout work only.
4. Find the classification of each sibling set.

An `expect` block in the model asserts a classification for one sibling set.
`adhcl validate` reports `failed_expectation` when an assertion is false.
If validation passes, each `expect` block holds.
The `adhcl diagram` page also shows each classification.
adhcl 0.2 has no command that prints matrices.
If no source gives a classification, report that gap.

Handle each classification as follows:

1. Uncoupled: no DP code can name a DP in another branch.
2. Decoupled: record the design order and the conclusions that an upstream change invalidates. Code can name another branch only where the model states a material influence.
3. Coupled: report the cycle and the model's `coupling` record. Generate iteration only from a stated loop bound, stopping rule, and failure behavior.
4. Unresolved: keep the unknown cells unknown. Report the missing evidence.

Design order is not runtime order.
Take runtime order from `flow` blocks only.
If generation needs a missing design decision, ask about that decision.
Meanwhile, generate only the parts that do not depend on it.

## 3. Make sure that the model fits the numbered layout

The numbered layout needs these model facts:

1. Each selected DP controls exactly one FR.
2. Each active FR, DP, and PV has a numbered alias, such as `FR2.1`, `DP2.1`, and `PV2.1`.
3. A DP has the number of the FR that it controls. A child extends its parent DP's number.
4. Each PV that is code realizes exactly one DP.

These are layout rules, not RequirementsHCL rules.
If a numbered alias is missing, propose the alias to the user.
Add it with the `adhcl` skill after the user agrees.
If a DP controls several FRs, do not split the DP or drop an FR.
In that case, keep the repository's own paths and report that the checker cannot compare the tree.

## 4. Generate the tree

For an existing repository, keep its paths, public names, and test layout.
Use the numbered layout only when the user approves the migration.
For a new tree, create these items from the model:

1. Create `src/dp<N>_<label>/` for each selected DP. Put each child DP folder directly in its parent's folder.
2. Put each PV that is code in the folder of the DP that it realizes. Use the model's `pv.address` when it gives one.
3. Start each PV file with a comment. The comment names the PV, the DP, the FR, and the module contract from the model.
4. Put the records and interfaces that children share in the parent's `contract/` folder.
5. Put the code that wires the children in the parent's PV. Take the wiring from the parent's `flow` blocks.
6. Put the composition of the top-level DPs in `src/app/`.
7. Name each new storage identifier with its owner's folder name and a separator, for example `dp2_2_fix_log/track.bin`.
8. Create `tests/fr<N>_<label>/` for each active FR, nested like the FR hierarchy.
9. Write one test for each scenario whose `verifies` list names a criterion of that FR. Make the test name its paired DP folder.
10. Put change scenarios (`kind = "change"`) in `tests/change/`.
11. Create `src/shared/` only for code that a model `constraint` requires. Name the constraint in each shared file.

A storage identifier is a table, file, key, or queue name.
With the folder name in it, a read of another DP's state shows in the matrix.
Do not rename an existing public storage identifier unless the user approves it.

If a PV describes a build step, a tool, or an external resource, keep that meaning.
Do not create a source module for that PV.
Report that the checker cannot compare it.

Take record fields and failure cases from the model's module contracts.
If a needed fact is missing, report the gap. Do not invent the fact.

For a structure-only request, give each unimplemented body the language's not-implemented error.
Examples are `throw new Error("not implemented")`, `todo!()`, `raise NotImplementedError`, and `throw UnimplementedError()`.
Mark each test for absent behavior as pending or skipped, with the missing behavior in its reason.
Never return a fake value that makes a test pass.
For an implementation request, implement the behavior and run the focused tests.

## 5. Run the checker

Run the checker from the project root:

```sh
python3 <skill-dir>/scripts/ad_layout_check.py --root . --spec <model path> --expect <policy>
```

1. Replace `<skill-dir>` with the directory of this skill.
2. Replace `<model path>` with the core file or the core directory. The checker does not read manifests or attachments.
3. Use `--src` and `--tests` if the roots are not `src/` and `tests/`.
4. If each sibling set is uncoupled, use `--expect uncoupled`.
5. If at least one sibling set is decoupled and none is coupled, use `--expect decoupled`.
6. If a sibling set is coupled or unresolved, omit `--expect`. Report why.

The checker needs Python 3.9 or later and no packages.
The `--expect` value is a structural policy that the checker enforces on the code.
It does not establish a classification.
If the user wants continuous integration, add the same command to it.

## 6. Act on the result

The matrices use these symbols:

1. `R`: code in the row's DP branch names the column's DP folder.
2. `.`: the scan found no reference.
3. `T`: test text in the FR folder names its paired DP. The checker does not run tests.
4. `?`: the FR folder has no test text that names its paired DP.

An error means a broken name, a broken pairing, a mismatch with the model, or a policy violation.
A warning means a reference that needs review. The model has a zero or no record for that cell.
A note gives context. For example, it names a material influence that no code reference shows.
Such an influence can use data or a shared resource. That is not a defect by itself.

If code names a DP where the model states a zero, stop.
Report the cell and the file. Ask the user which one changes: the code or the design.
For a design change, use `axiomatic-software-design`, then `adhcl`.
Do not hide a reference behind a path alias, a barrel file, an injection key, or a renamed identifier.
Do not edit the model to silence a finding.

Moving a call into a parent does not remove its effect.
A clean result covers code references only.
For each authored zero, also examine shared state, resources, configuration, and failure propagation.
Run the change and operational scenarios when an implementation exists.

## 7. Report the result

Report these items:

1. The generated or reviewed paths and their model IDs.
2. The `adhcl validate` command, exit code, and findings, or the reason that it did not run.
3. The checker command, exit code, matrices, and findings.
4. Each contradiction between code and an authored zero.
5. Each model gap, each unimplemented body, and each pending test.

State that an empty cell means that no code reference was found, not that the influence is absent.
Do not present a scaffold as an implemented or tested app.
Do not present a clean checker result as proof of independence.
