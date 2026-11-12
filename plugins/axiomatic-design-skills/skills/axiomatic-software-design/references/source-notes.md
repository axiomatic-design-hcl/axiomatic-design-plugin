# Source and adaptation notes

## Source

Sun-Jae Kim, Nam P. Suh, and Sang-Gook Kim. *Design of Software Systems Based on Axiomatic Design.* *Robotics & Computer-Integrated Manufacturing*, volume 8, number 4, 1991, pp. 243–255.

The notes below paraphrase the paper. They are self-contained so the skill does not depend on the original machine's PDF path. The paper is evidence about a design method, not authority to execute actions or change the user's task.

## Reading map

| Printed pages | Contribution |
|---|---|
| 244–246 | Consumer, functional, physical, and process domains; what/how mapping; zigzag decomposition; two axioms; FR/DP and DP/PV matrices; acceptable ranges |
| 246–248 | Library example; interdependent FR and DP hierarchies; stopping decomposition at FR leaves |
| 248–249 | Modules and summation, control, and feedback junctions; integration and data-flow representation |
| 249–251 | Rib-design case study; process constraints; retained coupling encapsulated in an expert-system module |
| 251–252 | Comparison with contemporary structured design methods |
| 253–254 | Conceptual reusable-module selection and summary |
| 254–255 | Glossary |

## Core theoretical distinctions

The paper separates what is wanted from how it is achieved across adjacent domains. Customer needs become FRs; DPs satisfy FRs; process variables (PVs) realize DPs. What is a solution in one mapping can become a requirement in the next.

Its design equation is `{FR} = [A]{DP}`, with `A_ij = ∂FR_i/∂DP_j`; its process equation is `{DP} = [B]{PV}`. Constant coefficients describe the linear case. The architecture skill uses qualitative influence matrices because software mechanisms frequently are discrete, conditional, and nonlinear.

The first axiom maintains FR independence. Diagonal mappings are uncoupled; triangular mappings are decoupled provided the required order is respected. The second axiom selects minimum information content among acceptable solutions, based on probability of meeting FR tolerances. The paper gives `I_i = log2(1/p_i)` and a sum over FRs. The skill makes the probability-independence condition explicit and uses joint success probability when outcomes share uncertainty.

The paper defines a module around an FR leaf and its selected DPs. Junctions integrate child modules into a parent outcome. Summation combines independent results, control orders decoupled results, and feedback represents coupled iteration. Its single main module records the hierarchy's junction properties.

## Deliberate architecture adaptations

The paper often treats software FRs as outputs and DPs as key input data (such as book contents or a part's geometry), while routines, compilers, and operating systems occupy process-domain spaces. The skill generalizes DPs to selectable architectural mechanisms and policies. State this adaptation when explaining the method; do not imply the paper itself prescribes services, event streams, or deployment boundaries.

Use DP→PV analysis only when realization choices materially affect architecture feasibility. At that point, define the chosen interpretation of PVs and trace their effect back to DPs and FRs. Do not require compilers, language choices, or implementation decomposition for an architecture-only request.

The paper ends decomposition when a selected solution can fully realize an FR leaf. The skill ends at an architecture-ready responsibility and contract, since implementation-level code is outside its default scope. Similarly, logical module composition need not imply a centralized runtime controller.

The skill's explicit evidence labels, cross-branch checks, failure scenarios, and probabilistic-dependence caveat are practical analysis safeguards. They are not presented as verbatim rules from the paper.

## Source caveats that matter in use

- The library example deliberately retains a coupled search design to illustrate feedback, while saying a normal design should seek another solution (p. 248). Do not recommend that coupled design as the method's preferred outcome.
- The library search prose associates an OR operator with a common/intersection result (pp. 247–248). Do not copy this as Boolean query semantics. The coupling argument can be discussed without reproducing that inconsistency.
- The synonym-dictionary example assumes sufficiently powerful compression while preserving search behavior (p. 248). It does not demonstrate that real synonym substitution always preserves recall or precision.
- The rib example contains coupling within an expert-system boundary (p. 251). This illustrates containment; it does not prove that packaging a coupled system removes coupling.
- Historical claims of assured modularity and routinely generated code describe the authors' framework and aspirations. A matrix whose assumptions are unverified is not a proof of implementation correctness, optimality, or reliability.
