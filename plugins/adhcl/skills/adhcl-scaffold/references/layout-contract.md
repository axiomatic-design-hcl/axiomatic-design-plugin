# Numbered FR/DP/PV source layout

This contract places the design of an `.ad.hcl` model into a source tree.
Each folder name repeats a model ID.
`scripts/ad_layout_check.py` reads the tree, builds code-reference matrices, and compares them with the model.
The layout is optional. It is not part of RequirementsHCL.

## What the layout can show

A design matrix states how a change to each DP affects each FR.
Its rows are FRs. Its columns are DPs.
Code structure shows one path for such an effect: code of one DP names another DP.
In this layout, every such name spells a distinctive folder name, so a text scan finds it.

Read the scan as follows:

1. A reference from the code of DP i to the folder of DP j is a possible effect of DP j on FR i.
2. A reference beside an authored zero contradicts the model until a reviewer explains it.
3. No reference does not prove a zero. Shared state, resources, data, configuration, timing, and the operating system do not show in names.
4. A test reference shows traceability only. The checker does not run tests.

Thus the checker can refute an uncoupled claim, but it cannot prove one.
The justified zeros in the model remain the argument for independence.

## Names

Each FR, DP, and PV folder or file has this name:

```text
<kind><number>_<label>
kind    = fr | dp | pv
number  = alias digits, with "_" for "."     FR2.1 -> 2_1
label   = snake_case label from the model    fr "sample_position" -> sample_position
grammar = ^(fr|dp|pv)([0-9]+(?:_[0-9]+)*)_([a-z][a-z0-9]*(?:_[a-z0-9]+)*)$
```

Examples are `fr2_1_sample_position`, `dp2_1_sampling_policy`, and `pv2_1_location_sampler`.
These names are valid package and module names in most languages.
A file name ends at its first dot, so `pv2_1_location_sampler.test.ts` belongs to PV2.1.
Several files can share one PV name, for example a `.h` file and a `.c` file.
A file can also repeat its own folder's name, for example `dp1_map/dp1_map.go`.

The model supplies the numbers through `alias` values such as `FR2.1`, `DP2.1`, and `PV2.1`.
A DP has the number of the FR that it controls.
A PV has the number of the DP that it realizes.
A child's number extends its parent DP's number by one position.

Numbers are stable identifiers, not positions.
When a sibling is added or removed, do not renumber the others. Use the next free number.
When a label changes, rename the folder and every reference to it in the same change.

## Tree

```text
spec/                         the .ad.hcl model
src/
  app/                        composition of the top-level DPs
  shared/                     optional: only code that a model constraint requires
  dp<N>_<label>/              one folder for each selected DP
    contract/                 parent DPs only: records and interfaces that the children share
    pv<N>_<label>[.ext]       the PV that realizes this DP (in a parent, it wires the children)
    dp<N>_<k>_<label>/        a child DP, directly inside its parent
    <other files>             private to this DP
tests/
  fr<N>_<label>/              one folder for each active FR, nested like the FR hierarchy
    scenario_<label>[.ext]    one test for each scenario that verifies a criterion of this FR
    fr<N>_<k>_<label>/        a child FR, directly inside its parent
  change/                     change scenarios: vary one DP and observe several FRs
```

Put each top-level `dp` folder directly in the source root.
Put each top-level `fr` folder directly in the test root.
Put each child folder directly in its parent's folder, with no folder between them.
Put each PV file or folder directly in the folder of the DP that it realizes.
If the language needs other file names, make the PV a folder and follow the language inside it.
If the language needs a different source root, pass that root with `--src`.

The example model `examples/trailhead/trailhead.ad.hcl` gives this tree:

```text
src/
  app/
  dp1_map_pack_renderer/pv1_tile_pack_renderer.ts
  dp2_track_recorder/
    contract/                 the Fix record
    pv2_fix_pipeline.ts       wires the sampler to the log
    dp2_1_sampling_policy/pv2_1_location_sampler.ts
    dp2_2_fix_log/pv2_2_preallocated_log.ts
  dp3_sos_beacon/
    contract/                 the PositionResult record
    pv3_sos_sequence.ts
    dp3_1_fix_acquirer/pv3_1_fix_request.ts
    dp3_2_sms_dispatcher/pv3_2_sms_handoff.ts
  dp4_forecast_cache/pv4_forecast_fetcher.ts
tests/
  fr1_show_map/
  fr2_record_track/
    fr2_1_sample_position/
    fr2_2_persist_fixes/
  fr3_send_sos/
    fr3_1_obtain_fix/
    fr3_2_deliver_message/
  fr4_show_forecast/
  change/
```

## Parents, contracts, and wiring

A parent DP is chosen before its children, so its decisions bind them.
The parent's `contract/` folder holds the records and interfaces that the children exchange.
Take the contract from the parent's `responsibility` and from the child modules' `inputs` and `outputs`.
The parent's PV holds the code that wires the children.
Take that wiring from the `flow` blocks that the parent's composite module owns.

A child depends on its parent's contract, not on a sibling.
When a child needs data from a sibling, the parent passes the data through the contract.
A change to the contract is a change to the parent DP.
It can still affect several child FRs. The model must state those effects.
Wiring through a parent does not remove an effect through data or shared state.

`src/app/` composes the top-level DPs.
Files directly in the source root, such as `src/lib.rs` or `src/index.ts`, follow the same rule.
The composition root has no DP of its own, because the design root is not a DP.

## Reference rules

A reference is text in a file that spells a `dp` folder name as a whole token.
It can be an import path, a package name, a storage identifier, or a configuration key.
When one line names a folder and its child folder, as in a path, the child counts.

| Code in | Can name | Must not name |
|---|---|---|
| `src/dp<N>_*` | its own subtree, and the `contract/` of each ancestor | DPs in other branches, unless the model states a material influence |
| `src/app/` and files directly in the source root | top-level `dp` folders | nested `dp` folders |
| `src/shared/` | no `dp` folder | every `dp` folder |
| `tests/fr<N>_*` | the paired `dp<N>` subtree | (other names are listed apart from the code matrix) |
| `tests/change/` | any `dp` folder | (no matrix row) |

The checker accepts any reference to an ancestor.
Review by hand that such a reference reaches only the ancestor's `contract/`.

Make references visible:

1. Spell the target folder name in every import across folders. Do not hide it behind a path alias, a barrel file, or an injection key.
2. In a new project, start each storage identifier with the owner's folder name and a separator, for example `dp2_2_fix_log/track.bin` or `dp2_2_fix_log.points`.
3. Name configuration keys the same way.
4. In an existing project, rename a public storage identifier only when the user approves it.

The separator must not be a letter, a digit, or an underscore.
The checker reads `dp2_2_fix_log_points` as an unknown folder name and reports an error.

## Shared code

`src/shared/` is not a convenience folder.
A change in shared code can change every FR that uses it.
Put code there only when a model `constraint` requires it, such as a protocol version.
Name that constraint in a comment in each shared file.
Shared code must not name a `dp` folder.

## Tests

Each active FR gets a `tests/fr*` folder that mirrors the FR hierarchy.
Each scenario whose `verifies` list names a criterion of that FR gets one test in that folder.
Write the scenario's `steps` as the test's steps.
The test names its paired DP folder. That reference supplies `T` on the matrix diagonal.
A test for a parent FR holds the parent's own criteria.
A scenario that verifies criteria of several FRs gets one test in each FR folder, or one shared fixture.
Change scenarios go in `tests/change/`, because they vary one DP and observe several rows.

## What the checker computes

The checker runs these steps:

1. It reads the `dp` tree under the source root and the `fr` tree under the test root. It checks names, nesting, and numbering.
2. It pairs `fr<N>` with `dp<N>`. An unpaired folder is an error.
3. It scans each text file for whole-token `dp` folder names. It assigns each file to its deepest enclosing `dp` or `fr` folder.
4. It turns each reference across branches into an `R` cell. The row is the FR paired with the referring folder. The column is the named DP.
5. It builds one matrix for each sibling set and one master matrix of leaf FRs by leaf DPs.
6. It reports each matrix pattern as diagonal, acyclic with a DP order, cyclic, or incomplete.
7. With `--spec`, it compares the tree with the model and the `R` cells with the authored influences.
8. With `--expect`, it enforces a structural policy.

A reference across branches appears where the branches meet and in the master matrix.
A reference from a parent's own code cannot resolve to a leaf cell. The master matrix lists it as unresolved.

The model comparison reports these findings:

1. An error for a missing, extra, or renamed folder, a missing PV entry, or a `pv.address` that differs from the path.
2. A review warning for an `R` cell where the model states a zero. Under `--expect`, this is an error.
3. A warning for an `R` cell where the model has no influence record for the cell or an ancestor cell.
4. A note for a material influence across branches that no code reference shows.

A reference counts for its own cell and for each ancestor cell.
For example, code in `dp3_2_sms_dispatcher` that names `dp2_2_fix_log` counts for FR3.2 <- DP2.2 and for FR3 <- DP2.
A `cells` block with `unlisted = "none"` counts as a zero for each unlisted cell of its sibling set.
The finding lists the conditions and premises of each zero. The checker does not resolve them.

The policies are:

1. `--expect uncoupled`: each reference across branches is an error.
2. `--expect decoupled`: a reference cycle is an error.
3. Under each policy, a reference beside an authored zero is an error.

Take the policy from the model's classification. The skill describes the selection.

Exit code `0` means that the checker found no error.
Exit code `1` means that it found at least one error.
Exit code `2` means that the command line is invalid.
Exit code `0` does not mean that the design is independent.

## Model input limits

`--spec` accepts one core `.ad.hcl` file or a directory of core files.
It reads a static subset of the language. It is not `adhcl validate`.
It reads quoted strings, numbers, Booleans, static references, lists, and literal objects.
Each attribute needs its own line. One attribute can sit inline in a block.

The reader stops with an error for manifests, attachments, `decision` blocks, and `evidence` blocks.
It also stops for heredocs, templates, and computed expressions.
It does not select a candidate or a context.
It reads `expect`, `coupling`, `module`, `flow`, and `scenario` blocks without assessing them.

The scan skips hidden paths and the folders `node_modules`, `__pycache__`, `build`, `dist`, `target`, and `vendor`.
It reports symbolic links, unreadable files, and files over 2,000,000 bytes as errors.
These paths prevent a complete matrix.

## Mapping to the model

| Layout item | Model field |
|---|---|
| `src/dp<N>_<label>/` | `dp "<label>"` with `alias = "DP<N>"` and `decision = "selected"` |
| `pv<N>_<label>` | `pv "<label>"` with `alias = "PV<N>"`, `realizes = [dp.<label>]`, and an optional `address` from the project root, without a file extension |
| `contract/` of a parent | the parent DP's `responsibility` and its children's module `inputs` and `outputs` |
| wiring in a parent PV | the `flow` blocks of the parent's composite module |
| `src/app/` | the root composite module that `contains` the top-level modules |
| storage identifiers | the `state` blocks in the DP's `owns_state` |
| `tests/fr<N>_<label>/scenario_<s>` | `scenario "<s>"` whose `verifies` names a criterion of `fr "<label>"` |
| `tests/change/scenario_<s>` | `scenario "<s>"` with `kind = "change"` |
