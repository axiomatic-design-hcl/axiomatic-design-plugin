---
name: adhcl
description: "Translate an existing Axiomatic Software Design into RequirementsHCL .ad.hcl files, and inspect those files with an available adhcl tool. Use for writing, updating, repairing, or reviewing .ad.hcl syntax, converting FR/DP hierarchies or influence tables into HCL, creating .ad.project.hcl manifests and .ad.ext.hcl attachments, or requesting RequirementsHCL reports. Use even when the user calls this design serialization or design-to-HCL conversion. This is the language and tool skill, not the axiomatic-software-design method skill."
---

# ADHCL authoring

Translate the supplied design into `requirements_hcl/core/1` files.
Preserve its requirements, choices, conditions, and evidence limits.
Use `axiomatic-software-design` for design decisions, not for language syntax.

A functional requirement (FR) states an outcome.
A design parameter (DP) controls an outcome.
A process variable (PV) realizes a DP.
An influence states how a DP affects an FR.

## Read the contracts

Read [the authoring guide](references/authoring.md) before converting a design.
Read [the field schema](references/schema.md) before writing blocks.
Read [the tool guide](references/tool-usage.md) before invoking a tool.
The schema defines exact fields, types, and allowed omissions.

Read [the language reference](references/language.md) for expressions, file selection, attachments, and report meanings.
Read [the assessment contract](references/assessment-contract.md) for candidates, contexts, inherited metadata, assertions, or empirical evidence.
Read [the diagnostic contract](references/diagnostics.md) when interpreting findings or selecting a review profile.
These bundled contracts are unchanged copies of this specification.

If the target repository supplies newer contracts, read those contracts first.
Do not mix incompatible versions.
If installed tool help conflicts with the target contract, report that mismatch before claiming language conformance.

## Preserve the design

Treat the design from `axiomatic-software-design` as the input, not as permission to redesign the system.
Retain all distinct FRs, DPs, alternatives, and cross-branch effects.
Keep unknown facts unknown.
Ask only when missing information prevents a faithful representation.

If a design decision is missing, use `axiomatic-software-design` for that decision.
Do not add a mechanism, threshold, module, or probability to satisfy a profile.
If a source states a qualitative criterion, retain its statement without invented measurements.
Report the resulting gap.

## Write the files

Use one `.ad.hcl` file for a small design.
For larger designs, split by domain and branch.
Keep each branch's FRs, DPs, influences, and decisions together.
Put cross-branch influences with their nearest common parent.

Create exactly one design root across the core files.
Use snake_case labels and typed references.
Retain source IDs in `alias` where the schema permits it.
Record sources and provenance without claiming that a citation proves the design.

Write each supplied fact once.
Do not author matrix data, numbering, classification, junctions, information scores, or implementation status.
Use `expect` only for a requested assertion, not as a source of facts.
Do not add assertions to force the design's preferred conclusion.

If external bindings, behavior links, or presentation data are requested, put them in attachments.
Use an explicit manifest to list those attachments and their extension owners.
Do not introduce core `import`, `module.handles`, or compatibility aliases.

## Make sure that the result matches

Make sure that all in-scope design facts appear without changes to their meaning.
Make sure that every field matches its schema table.
Make sure that references resolve across the selected core files.
Keep missing facts separate from malformed syntax.

Make sure that child FRs name parent DPs, not parent FRs.
Make sure that `controls` does not substitute for a material influence.
Make sure that each zero has a reason and each material effect has a mechanism.
Do not infer influence from calls, module dependencies, or runtime order.

Use the tool guide to exercise the selected files.
Repair syntax or reference mistakes without changing the design to silence findings.
If a profile requires absent design facts, report those gaps instead.
A successful native HCL parse does not establish typed resolution or design support.

## Deliver the result

Write the requested files to the target location.
Report the input path that selects them.
State which tool commands ran and what they established.
If no language tool is available, state that full validation did not run.

Keep the final explanation shorter than the generated model.
Name unresolved facts and unavailable prerequisites.
Do not present proposed scenarios as completed tests or declarations as implemented software.
