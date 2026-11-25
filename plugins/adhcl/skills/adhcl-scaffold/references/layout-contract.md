# FR/DP/PV source layout contract

This contract places the design of a `.ad.hcl` model into a source tree.
The folder names repeat the model's identifiers.
A tool can then rebuild each design matrix from the tree and compare it with the model.
`scripts/ad_layout_check.py` implements the checks in this contract.

## What the layout can and cannot show

A design matrix states how a change to a DP affects an FR.
Code structure shows only one kind of path for that effect: one module names another.
The layout makes such paths visible, because every cross-module reference must spell a distinctive folder name.

Treat the result as follows:

- A reference from the code of DP i to DP j is evidence of a material effect of DP j on FR i.
- No reference is not evidence of a zero. Shared runtime resources, data, configuration, timing, and the operating system are invisible to a text scan.
- A diagonal cell is confirmed only when a test in `tests/fr<N>_*` reaches `src/dp<N>_*`.

The checker can therefore refute an uncoupled claim, but it cannot prove one.
The justified zeros in the model remain the argument for independence.

## Names

Every FR, DP, and PV folder or file has this name:

```text
<kind><number>_<label>
kind    = fr | dp | pv
number  = the alias digits with "_" for "."     FR2.1 -> 2_1
label   = the snake_case label from the model   fr "sample_position" -> sample_position
```

Examples: `fr2_1_sample_position`, `dp2_1_sampling_policy`, `pv2_1_location_sampler`.
The full grammar is `^(fr|dp|pv)([0-9]+(?:_[0-9]+)*)_([a-z][a-z0-9]*(?:_[a-z0-9]+)*)$`.
Names start with a letter and contain only lowercase letters, digits, and underscores.
They are valid package and module names in most languages.

The model supplies the numbers through `alias` values such as `FR2.1`, `DP2.1`, and `PV2.1`.
A DP has the number of the FR it controls.
A PV has the number of the DP it realizes.
A child's number extends its parent DP's number by one position.

Numbers are stable identifiers, not positions.
Do not renumber when a sibling is added or removed; use the next free number and leave gaps.
A rename of a label renames the folder and every reference to it in the same change.

## Tree

```text
spec/                         the .ad.hcl model
src/
  app/                        design root: composition of the top-level DPs
  shared/                     optional; only code that a constraint mandates
  dp<N>_<label>/              one folder per selected DP
    contract/                 parent DPs only: records and interfaces that the children share
    pv<N>_<label>[.ext]       the PV that realizes this DP; for a parent, the junction wiring
    dp<N>_<k>_<label>/        child DPs, nested by number
    <other files>             private to this DP
tests/
  fr<N>_<label>/              one folder per active FR, nested like the FR hierarchy
    scenario_<label>[.ext]    one test per scenario that verifies a criterion of this FR
  change/                     change scenarios that vary one DP and observe several FRs
```

Place a top-level `dp` folder directly in `src/`, and a top-level `fr` folder directly in `tests/`.
Place a child folder directly in its parent's folder.
Place a `pv` file or folder directly in the folder of the DP that it realizes.
A PV can be a file or a folder; when a language requires other file names, make the PV a folder and put the files inside.

`app/` is the root junction.
It has no DP of its own, because the design root is not a DP.
It composes the top-level DPs and nothing deeper.

## Parent DPs, contracts, and junctions

A parent DP is chosen before its children.
Its decisions bind the children, so they live in the parent's folder:

- `contract/` holds the records and interfaces that the children exchange, for example a `Fix` record that a sampler produces and a log stores. Derive it from the parent DP's `responsibility` and from the child modules' `inputs` and `outputs`.
- The parent's PV holds the junction: the code that wires the children. Derive the wiring from the model's `flow` blocks.

A child depends on its parent's contract, never on a sibling.
When a child needs data from a sibling, the parent passes it through the contract.
The contract is a parent decision, so a change to it is a change of the parent DP, which the parent row of the matrix already covers.

## Reference rules

A reference is any text in a file that spells the name of a `dp` folder as a whole token: an import path, a package name, a storage key, or a configuration key.

| Code in | May refer to | Must not refer to |
|---|---|---|
| `src/dp<N>_*` | its own subtree; the folders of its ancestors, for their `contract/` | sibling and cousin `dp` folders |
| `src/app/` | top-level `dp` folders | nested `dp` folders |
| `src/shared/` | nothing in any `dp` folder | every `dp` folder |
| `tests/fr<N>_*` | the paired `dp<N>` subtree; ancestor contracts | every other `dp` folder |
| `tests/change/` | any `dp` folder | (no matrix row) |

A reference to an ancestor should reach only its `contract/`.
The checker allows any reference to an ancestor, so review such references by hand.

For a decoupled design, a reference across siblings is permitted only where the model states a material influence from that DP to this FR.
For an uncoupled design, no such reference is permitted.
The checker reports a reference that contradicts an authored `effect = "none"` as an error, and a reference to a cell without an authored effect as a warning.

Make references visible:

- Spell the target folder name in every cross-folder import. Do not hide it behind path aliases, barrel files, or dependency-injection keys that omit the name.
- Prefix every storage identifier with the owning DP's folder name, for example the table, file, or key `dp2_2_fix_log.track_log`. A read of another DP's state then appears as a reference.
- Name configuration keys the same way.

## Shared code

`shared/` is not a convenience folder.
A change in shared code can change every FR that uses it, so shared code is a constraint, not a DP.
Put code there only when a model `constraint` mandates it, such as a mandated unit system or a protocol version.
Name the constraint in a header comment of each shared file.
Shared code must not refer to any `dp` folder.

## Tests

Each active FR gets a `tests/fr*` folder that mirrors the FR hierarchy.
Each scenario whose `verifies` list names a criterion of that FR gets one test in that folder.
Write the scenario's `steps` as the test's steps.
A test must exercise the paired DP: that reference is the evidence for the diagonal cell.

A parent FR's folder holds tests for the parent's own criteria.
A scenario that verifies criteria of several FRs gets one test in each FR folder.
Change scenarios go in `tests/change/`, because they vary one DP and observe several rows.

## What the checker computes

`ad_layout_check.py` runs these steps:

1. It reads the `dp` tree under `src/` and the `fr` tree under `tests/`, and it checks names, nesting, and numbering.
2. It pairs `fr<N>` with `dp<N>`. A test folder without a DP is an uncontrolled requirement. A DP without a test folder is a warning.
3. It scans each text file for whole-token `dp` folder names and attributes the file to its deepest enclosing `dp` or `fr` folder.
4. It turns each cross-folder reference into evidence for a cell: the row is the FR paired with the referring folder, and the column is the referenced DP.
5. It builds one matrix per sibling set and one master matrix of leaf FRs by leaf DPs. Evidence between two branches appears at the level where the branches meet and in the master matrix.
6. It classifies each matrix as uncoupled, decoupled with a DP order, or coupled.
7. With `--spec`, it compares the tree with the model: missing or extra folders, renamed labels, missing PVs, `pv.address` values, and every authored `effect = "none"` that code evidence contradicts.
8. With `--expect`, it fails when a matrix is worse than the expected classification.

Exit code 0 means no error finding.
It does not mean that the design is independent.

## Mapping to the model

| Layout item | Model field |
|---|---|
| `src/dp<N>_<label>/` | `dp "<label>"` with `alias = "DP<N>"` |
| `pv<N>_<label>` | `pv "<label>"` with `alias = "PV<N>"`, `realizes = [dp.<label>]`, and `address` set to its path from the project root, without a file extension |
| `contract/` of a parent | the parent DP's `responsibility` and its children's module `inputs` and `outputs` |
| parent PV (junction) | the `flow` blocks owned by the parent's composite module |
| `src/app/` | the root composite module, which `contains` the top-level modules |
| storage identifiers | `state` blocks in the DP's `owns_state` |
| `tests/fr<N>_<label>/scenario_<s>` | `scenario "<s>"` whose `verifies` names a criterion of `fr "<label>"` |
| `tests/change/scenario_<s>` | `scenario "<s>"` with `kind = "change"` |

The checker requires these preconditions in the model:

- Every selected DP controls exactly one FR, and both have matching numbered aliases.
- Every PV realizes exactly one DP.
- Rejected, proposed, and superseded DPs get no folder.
