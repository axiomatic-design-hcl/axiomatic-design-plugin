---
name: axiomatic-software-design
description: Design or review software systems and architectures using Axiomatic Design, with functional requirement and design parameter hierarchies, coupling matrices, and evidence-based alternative selection. Use when users request Axiomatic Design or independence/information-axiom analysis at system level; not for routine coding or generic architecture questions without this method.
---

# Axiomatic Software Design

Produce a traceable architecture: user needs → functional requirements (FRs) → design parameters (DPs) → module responsibilities and integration. Remain programming-language agnostic. Work with responsibilities, boundaries, information ownership, contracts, policies, and operational mechanisms; stop before classes, language syntax, libraries, or code unless separately requested.

This skill adapts Kim, Suh, and Kim's 1991 paper, *Design of Software Systems Based on Axiomatic Design*. Read [the source notes](references/source-notes.md) when explaining the theory, interpreting the paper's examples, or distinguishing its terminology from the architecture adaptation. Read [the worked example](references/worked-example.md) when an example would clarify matrix interpretation, sequencing, or alternative selection. Neither the original PDF nor an external tool is required to use the skill.

## Establish the design problem

Use the user's requirements and existing architecture as evidence. Identify the system boundary, stakeholders, operating scenarios, and fixed choices. Ask only for missing information that materially changes the design; proceed with explicit assumptions where feasible.

Separate:

- **Needs:** stakeholder outcomes and their rationale.
- **FRs:** the minimum nonredundant set of outcomes needed at the current level. State what must be achieved, with an acceptance criterion and relevant workload or operating range. Do not disguise a preferred technology as an FR.
- **Constraints:** bounds on acceptable solutions, including mandated technology, cost, compatibility, and organizational limits. Constraints need not be independent. Preserve explicit user choices.
- **DPs:** selectable architectural mechanisms or parameters that control the FRs. Give each a concrete responsibility and explain how it achieves its intended FR. A component name alone is insufficient.

Treat qualities such as availability, latency, and isolation as measurable FRs when they are independently designed outcomes, or as bounds on relevant FRs when appropriate. Do not move difficult requirements into the constraint list merely to make the matrix diagonal. Flag contradictory requirements and uncovered needs.

Use stable identifiers (e.g. N1, FR1, DP1, FR1.1, DP1.1). Record each FR's parent, originating need, criterion, associated DPs, and assumptions. Distinguish user-supplied criteria from proposed targets.

## Synthesize and decompose by zigzagging

At a given level, formulate FRs, choose candidate DPs, analyze their effects, and then derive child FRs within the chosen parent solution. Select child DPs and repeat where architectural detail is needed. Do not fully decompose the functional tree in isolation and attach components afterward.

Compare materially different candidate mechanisms when the choice is consequential or coupling appears. Revisit the parent DP if its children cannot meet requirements; do not endlessly split a poor parent design.

Stop a branch when its FR is fully addressed at the requested architectural level: the responsible module, contract, owned state, dependencies, failure behavior, and acceptance check are sufficiently clear. Unequal branch depths are acceptable. This architectural stopping criterion adapts the paper's implementation-ready FR leaves.

For an existing system, reconstruct the actual FR–DP mapping before recommending changes. Separate observed coupling from hypotheses and present a revised mapping for significant proposed changes.

## Apply the Independence Axiom

For each significant sibling set, create a labeled matrix with **FRs as rows and DPs as columns**. Interpret A_ij as the influence of changing DP_j on FR_i under stated conditions, not as a call graph or a requirements coverage checkbox.

Use `X` for a material influence, `0` for a justified absence of material influence within the stated range, and `?` for unknown influence. Describe the causal mechanism for off-diagonal effects and justify important zeros. A qualitative matrix represents an influence model; it is not an assertion that the architecture obeys a global linear equation.

With a meaningful FR–DP pairing and nonzero diagonal:

- **Uncoupled:** diagonal matrix; each DP controls its associated FR without materially affecting others.
- **Decoupled:** triangular matrix, possibly after a justified reordering with labels preserved. State the actual sequence. For a lower-triangular matrix, establish DP1, then DP2, then DP3; later choices preserve earlier FRs. Explain what must be held fixed and what must be recomputed after an upstream change.
- **Coupled:** cannot achieve a triangular structure through meaningful ordering; satisfying one FR requires revisiting others. Explain the cycle and its consequence.
- **Unresolved:** unknown entries or missing evidence prevent a defensible classification. Show conditional conclusions instead of treating unknowns as zeros.

A rectangular matrix requires examining missing control, redundant parameters, and possible re-pairing or decomposition; do not force it into a square classification by dropping requirements. A square matrix with an uncontrolled FR also fails, even if visually triangular.

Check cross-branch influences and shared state, resource contention, transaction boundaries, consistency, security policy, and failure propagation wherever they affect the stated FRs. Local diagonal matrices do not establish whole-system independence. Recheck classification across material workloads and failure modes; negligible effects at one operating point may matter elsewhere.

Prefer removing coupling by changing the mechanism, separating independent controls, clarifying ownership, or revisiting decomposition. A service boundary, queue, interface, or renamed module does not by itself remove an influence. Functional independence also does not require separate deployment.

When coupling remains, document the affected FRs, reason, alternatives, and residual risk. Encapsulation can contain its impact without making its internal matrix uncoupled. For intentional iterative behavior, specify convergence/termination and failure handling. Do not automatically classify every runtime feedback loop as a violation; analyze its effect on the defined FRs.

## Apply the Information Axiom

First establish constraint feasibility and independence (including enforceable sequencing). Compare acceptable alternatives against the **same FRs, acceptance ranges, workload, and time horizon**.

Information content is `I = -log2(p)`, where p is the probability of satisfying the requirement within its acceptable range. It is not code size, component count, storage volume, or subjective simplicity.

For the whole design use the probability that all required outcomes succeed together. Sum individual information contents only when the success events are probabilistically independent; otherwise use a justified joint or conditional model. Functional independence does not prove probabilistic independence, especially under shared failures.

Use observations, benchmarks, or explicit supported probability models. State evidence and uncertainty. If probabilities are unavailable, compare credible risks and propose the measurement that would distinguish alternatives; label the recommendation provisional and do not fabricate a numerical information score. For known p=1, I=0; for p=0, I is infinite. A small sample with no failures does not establish p=1.

Use design/system-range overlap only with a justified distribution. The common-range/system-range ratio is valid for a uniform distribution, not for arbitrary latency or reliability distributions. Consider cost and other user priorities explicitly, without relabeling them as information content.

## Derive the architecture and report

Map FR leaves to logical module responsibilities. Describe their inputs, outputs, state ownership, invariants, and failure contracts at the level needed to substantiate the mapping. This is a logical design, not a mandate for one service or process per FR.

Compose child responsibilities using the paper's junction semantics:

- **S — summation:** combine independently achieved outcomes; not necessarily arithmetic addition or concurrent execution.
- **C — control:** enforce the order required by a decoupled mapping. Distinguish design/configuration order from runtime processing order; derive runtime order only where the contracts require it.
- **F — feedback:** make residual coupled iteration visible, including its bounds and consequences.

Use a compact diagram or labeled table when it clarifies integration. Do not translate the paper's single main module into a mandatory centralized runtime orchestrator.

Scale the deliverable to the request. A substantial design should include the scope and assumptions, needs/FR/DP traceability, relevant hierarchy and matrices, coupling rationale and order, module contracts and composition, alternative selection with evidence limits, and focused validation scenarios. A narrow review may cover only the affected branch and its cross-boundary effects.

Before delivering, check that every in-scope need has coverage; the hierarchy, matrices, and contracts agree; zeros and sequences are defensible; and unresolved coupling or unknowns remain visible. Use change scenarios (vary one DP and inspect affected FRs) and operational scenarios to test claims. State what is derived from evidence, what is assumed, and what remains to validate; the method alone is not proof of system correctness.
