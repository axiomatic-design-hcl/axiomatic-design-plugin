# Design-to-HCL guide

Use the supplied design as the source of facts.
Read `schema.md` for exact fields before writing each block type.
The examples below illustrate syntax, not measurements or supported independence.

## Map the input

Translate the design through these steps:

1. Map the system boundary to one `design` block.
2. Map stakeholder outcomes to `need` blocks.
3. Map solution limits to `constraint` blocks.
4. Map operating premises to `assumption`, `context`, and `workload` blocks.
5. Map outcomes to `fr` blocks with the supplied criteria.
6. Map mechanisms to `dp` blocks with their actual lifecycle decisions.
7. Map stated effects to unlabeled `influence` blocks.
8. Map supplied alternatives to nested `candidate` blocks inside `decision` blocks.
9. Map supplied logical boundaries to `module` blocks.
10. Map supplied realizations to `pv` blocks.
11. Map supplied runtime sequences to `flow` blocks.
12. Map proposed acceptance procedures to `scenario` blocks.

An omitted source fact remains a gap.
Do not create every block type for every model.
Do not treat a proposed architecture as observed implementation.

## Labels and references

Use labels that match `^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$`.
Labels are unique within each block namespace across the merged core.
Use `alias = "FR1"` to retain a source ID on an FR.

Use traversals such as `fr.admit`, not strings such as `"fr.admit"`.
Use `fr.admit.criterion.valid` for a nested criterion.
Use `decision.storage.candidate.local` for a nested candidate.
The design label does not prefix these paths.

## Hierarchy and acceptance

Root FRs require a `need` reference or nonempty list of need references.
Child FRs use `parent = dp.parent_control`.
A DP requires a nonempty `controls` list, a `responsibility`, and a `decision`.
A DP has no `parent` field.

Each DP's controlled FRs must share one sibling set.
Retain a DP that controls several FRs as one DP.
Do not drop requirements or duplicate controls to create a square matrix.

A criterion requires a qualitative `statement`, a complete `metric`/`op`/`value` triple, or both.
A criterion's `origin` is `user`, `source`, or `proposed`.
Do not use `origin = "inferred"` on a criterion.

For `op = "in"`, `[1, 10]` means two allowed values.
For an inclusive interval, use `{ min = 1, max = 10 }`.
Only write limits that the source supplies or the user approves.

A child criterion can use `allocated_from = fr.parent_outcome.criterion.limit`.
This link records allocation, not proof that child outcomes satisfy the parent.
Do not copy parent acceptance targets onto children without a stated allocation.

## Influences and unknowns

Read the input matrix with FR rows and DP columns.
Translate each supported source claim with its operating conditions.
The source's matrix is input evidence, not a generated matrix to store in HCL.

Translate entries as follows:

1. Map `X` to `effect = "material"` with the supplied mechanism.
2. Map `0` to `effect = "none"` with the supplied reason in `because`.
3. Map `?` to `effect = "unknown"`, or leave an absent relation absent.

If a zero lacks a reason, retain the stated zero only after obtaining its reason.
Until then, represent that relation as unknown and report the unsupported zero.
If a material claim lacks a mechanism, represent the gap without inventing a causal explanation.
Do not treat a proposed control pairing as its diagonal influence.

Use `from = [dp.control]` and `to = fr.outcome`.
A multi-member `from` list asserts each effect independently.
It cannot represent an effect that occurs only when several controls change together.
For such an interaction, report the language limit without rewriting the design.

Use `under = context.normal` or `under = workload.requests` for named applicability.
Use `holds_if` for assumption references.
Mark an added explanation with `mechanism_source = "inferred"` only when inference is explicitly part of the task.

Use `cells` only when the supplied argument covers every unlisted sibling cell in that scope.
A default zero requires `because`.
It cannot fill cross-branch cells or turn an explicit unknown into zero.
Parent effects do not automatically create descendant effects.

## Decisions and evidence

Preserve the actual choice in each DP's `decision` field.
Only `selected` DPs activate by default.
Candidate membership and default lifecycle states must agree.

List an alternative's DPs in its candidate's `dps` field.
Include required ancestors explicitly unless they are common selected DPs outside every candidate.
Do not assume that a candidate silently replaces one branch of another candidate.
Read `assessment-contract.md` before constructing alternative snapshots.

Use `information { basis = "unknown" }` when the design requests information analysis without qualified empirical evidence.
Use `provisional = true` for a provisional selection.
Do not write probability or information-score attributes.

For measured evidence, read every required field in `schema.md`.
Preserve exact candidate version, context, workload, horizon, predicates, trial counts, and sampling assumptions.
Zero observed failures do not establish certainty.
Different operating ranges do not support a like-for-like comparison.

## Modules and runtime behavior

A realization module uses `realizes = [dp.control]`.
A composite module uses `contains = [module.child]` instead.
A module cannot use both forms.

For the architecture profile, each active leaf DP needs exactly one realization module.
Its contract needs explicit inputs, outputs, state ownership, dependencies, invariants, failure behavior, and acceptance references.
Use empty ownership or dependency lists only when the design states that they are empty.
Do not use empty lists to hide missing information.

State ownership belongs to leaf DPs.
A realizing module can describe that same ownership.
Do not assign one state to several logical owners.

A flow's `steps` contain typed module, FR, or DP references.
A scenario's `steps` contain instruction strings.
A scenario's `verifies` contains criterion references, not FR references.

Each active leaf FR needs a scenario that covers all its applicable criteria for the architecture profile.
A runtime loop needs its actual endpoints, condition, and positive bound.
Residual coupled iteration also needs its separate coupling contract.
Do not infer runtime order from a triangular matrix alone.

## Syntax example

The source supplies one need, one outcome, a selected control, and its material effect.
It supplies a qualitative criterion but no module contract or measured evidence.
The model preserves those limits.

```hcl
source "design_note" {
  title = "Approved design note"
}

design "catalog" {
  boundary = "Catalog lookup only. Storage administration is outside the boundary."
}

need "find_items" {
  statement = "Find catalog items."
  origin = "user"
  cites = source.design_note
}

fr "lookup" {
  alias = "FR1"
  need = [need.find_items]
  statement = "Return matching catalog items."
  criterion "matches" {
    statement = "Return every matching item."
    origin = "source"
    cites = source.design_note
  }
}

dp "catalog_index" {
  alias = "DP1"
  controls = [fr.lookup]
  responsibility = "Use the catalog index to select matching items."
  decision = "selected"
}

influence {
  from = [dp.catalog_index]
  to = fr.lookup
  effect = "material"
  mechanism = "The index selection rule determines which matching items are returned."
  mechanism_source = "source"
  cites = source.design_note
}
```

Do not report that this example passes the architecture profile.
Its qualitative criterion, missing module contract, and absent scenario remain gaps.
Its citation does not establish substantive support.
