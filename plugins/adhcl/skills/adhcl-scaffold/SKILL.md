---
name: adhcl-scaffold
description: "Turn a RequirementsHCL .ad.hcl design into a source tree whose folders repeat the design's IDs: src/dp<N>_<label>/ per DP, pv<N>_<label> per PV, tests/fr<N>_<label>/ per FR, parent contracts, and junction wiring. Then rebuild the FR-DP matrices from the tree with the bundled layout checker and compare them with the model. Use when asked to scaffold, generate, or lay out an app or module structure from an .ad.hcl spec, to check that code still follows its axiomatic design, or to rebuild a design matrix from a src/ folder."
---

# Scaffold an architecture from an `.ad.hcl` model

Build the source layout that the model describes.
Every selected DP becomes a folder, every PV becomes a file or folder inside it, and every FR becomes a test folder.
The names repeat the model's IDs, so a tool can rebuild each design matrix from the tree.

The model is the input.
Do not redesign the system to fit the layout.
Use the `axiomatic-software-design` skill for design decisions and the `adhcl` skill for changes to `.ad.hcl` files.

## Read the contract

Read [the layout contract](references/layout-contract.md) before you create a folder.
It defines the names, the tree, the reference rules, and what the checker can and cannot show.
Read the `adhcl` skill's schema reference when you need the exact meaning of a model field.

## Check the model first

1. Run `adhcl validate` on the model, as the `adhcl` skill's tool guide describes. Record the classification of each scope and the master matrix.
2. Check the layout preconditions:
   - Each selected DP controls exactly one FR.
   - Each FR, DP, and PV has a numbered alias, such as `FR2.1`, `DP2.1`, and `PV2.1`. A DP's number equals the number of the FR it controls; a child's number extends its parent DP's number.
   - Each PV realizes exactly one DP.
3. If a precondition fails, propose the model change and make it with the `adhcl` skill after the user agrees. Do not invent numbers in the tree that the model does not carry.

Treat the classification as follows:

- **Uncoupled:** no `dp` folder may refer to a sibling or cousin `dp` folder.
- **Decoupled:** a reference across siblings may follow only a material influence that the model states, from an earlier DP in the design order to a later FR. Record that order in the parent's junction.
- **Coupled or unresolved:** report the cycle or the unknown cells. The layout cannot remove coupling. Scaffold that scope only if the user accepts it, and keep the coupled children inside their parent's folder, with the iteration in the parent's junction and the model's `coupling` record cited there.

## Choose the language

Use the language, framework, and build tool of the target repository.
If the repository has none and the user did not name one, ask.
Keep folder names exactly as the contract defines them.
When a language requires other file names, make each PV a folder and follow the language's conventions inside it.

## Generate the tree

Create these items from the model:

1. `src/dp<N>_<label>/` for each selected DP, nested by number. Give no folder to a rejected, proposed, or superseded DP.
2. `pv<N>_<label>` in the folder of the DP that it realizes. Start it with a header comment that names the PV, the DP, the controlled FR, and the module's contract from the model: inputs, outputs, owned state, invariants, and failure behavior.
3. `contract/` in each parent DP's folder. Define the records and interfaces that the children exchange, from the parent's `responsibility` and the children's module `inputs` and `outputs`. Use the record names that the model uses.
4. The junction in each parent's PV. Wire the children in the order of the parent's `flow` blocks. Pass data between children only through the parent's contract.
5. `src/app/` as the composition root. Compose the top-level DPs only.
6. Storage identifiers, such as table names, file names, and keys, that start with the owning DP's folder name, from each DP's `owns_state`.
7. `tests/fr<N>_<label>/` for each active FR, nested like the FR hierarchy. Add one test per scenario that verifies one of the FR's criteria. Write the scenario's steps as the test's steps, and make the test exercise the paired DP.
8. `tests/change/` for scenarios with `kind = "change"`.

Create `src/shared/` only for code that a model `constraint` mandates, and name that constraint in the file.
Do not move code there to avoid a reference rule.

Leave behavior unimplemented unless the user asks for an implementation.
Mark each unimplemented body with the language's not-implemented error, so that a test fails instead of passing.
If the model lacks a fact that a contract needs, such as a record field or a failure case, report the gap instead of inventing the fact.

When `pv.address` is absent from the model, propose the address of the generated path and add it with the `adhcl` skill after the user agrees.

## Check the tree

Run the bundled checker from the project root:

```sh
python3 <skill-dir>/scripts/ad_layout_check.py --root . --spec <model path> --expect <classification>
```

Use the classification that `adhcl validate` reported for the model, `uncoupled` or `decoupled`.
Use `--src` and `--tests` when the project keeps them elsewhere.
The checker needs Python 3.9 or later and no packages.

Read its output:

- Each matrix shows `X` for a cross-folder reference, `0` for no reference, and `?` for a diagonal that no test reaches.
- An error means a broken name or nesting, a mismatch with the model, a reference that contradicts an authored zero, or a scope worse than `--expect`.
- A warning means a missing pairing, a leaf DP without a PV, or a reference to a cell without an authored effect.
- A note means a material influence in the model that no code reference shows. Such an effect can travel through data or runtime behavior; that is not a defect by itself.

Fix the tree, not the model, until the checker reports no error.
If the code needs an influence that the model says is absent, stop and report it: the design or the code must change, and that decision belongs to the user.
Do not hide a reference behind a path alias, a barrel file, or a renamed key to pass the check.

## Keep the check running

Suggest running the checker in continuous integration with the same arguments.
The check then fails when a change adds a reference that the design does not allow.

## Deliver the result

Report the generated tree, the `adhcl validate` result, and the checker's command, exit code, and matrices.
State that a `0` cell means no code reference was found, not that the influence is absent.
Name every model gap and every unimplemented body.
Do not present a scaffold as an implemented or tested system.
