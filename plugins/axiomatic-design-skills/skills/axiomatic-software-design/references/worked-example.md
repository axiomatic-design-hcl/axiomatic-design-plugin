# Worked architecture example: invoice retention and delivery

This example is an original architecture-level adaptation, not a case study from the source paper. Its criteria and numerical probabilities are illustrative assumptions, not measured recommendations.

## Needs and first mapping

A business needs issued invoices retained and made available to customers. Assume the architecture must support a fixed invoice representation and use an existing external mail provider.

| ID | Outcome and assumed criterion | Selected DP |
|---|---|---|
| FR1 | Retain each issued invoice durably and retrieve its exact issued content | DP1: durable invoice ledger with immutable issued versions and stable IDs |
| FR2 | Submit a delivery notification for each issued invoice within 60 seconds under the agreed load | DP2: delivery worker with an independently configurable retry policy using committed invoice IDs |

Mail-provider choice is a constraint. The time target is a proposed FR acceptance bound. Actual receipt is not claimed: if the customer needs receipt rather than submission, revise FR2 and the design.

| A | DP1 | DP2 |
|---|---|---|
| FR1 | X | 0 |
| FR2 | X | X |

DP1 affects FR2 because delivery consumes its committed IDs and contents. DP2 does not alter retained invoice content if the worker has read-only invoice access and separate state/resources sufficient to prevent delivery load from compromising FR1. Those are conditions to validate, not universal zeros.

The mapping is decoupled under these assumptions. Establish the invoice ledger contract first, then configure the worker against that contract. A ledger contract change may require revisiting delivery. At runtime, commit the invoice before submitting notification. Design order and runtime order agree here because the contract explicitly requires committed data.

A proposed alternative that writes invoice data only after mail submission would make provider failure prevent invoice retention. Analyze that cross-effect rather than assuming two named modules imply independence.

## One zigzag step

After choosing the delivery worker, decompose FR2:

| Child FR | Child DP |
|---|---|
| FR2.1: retain delivery intent for every committed invoice across a crash | DP2.1: delivery-intent record committed atomically with issuance |
| FR2.2: submit pending intent to the provider within the target | DP2.2: dispatcher consuming pending records with bounded retries and stable delivery keys |

The child matrix is lower triangular: DP2.1 controls FR2.1 and supplies work for FR2.2; DP2.2 controls FR2.2. Its zero for DP2.2→FR2.1 assumes dispatch cannot erase unacknowledged intent. Stable keys alone do not guarantee exactly-once external mail delivery; the provider's contract determines duplicate behavior.

This decomposition exposes a cross-branch effect: adding an atomic intent write changes issuance's transaction. Revisit FR1's failure behavior and any latency constraints; do not infer whole-system independence solely from the child matrix. If a database or resource limit is unknown, mark the corresponding effect `?`.

Architecture leaves can now name owned state and contracts: the issuance boundary owns invoice versions and the atomic creation of intent; the dispatcher owns attempt state and consumes committed intent. They may run in one deployable application. A C junction records commit-before-dispatch. Crash after commit and before dispatch, repeated submission, and provider outage are material validation scenarios.

## Second-axiom comparison

Suppose two otherwise feasible candidates meet the independence analysis under the same workload and criteria. If evidence estimates their **joint** probability of meeting both FRs over the same test horizon as 0.99 and 0.95, their information contents are approximately 0.0145 and 0.0740 bits respectively. The first is preferred by the Information Axiom, subject to constraints and the uncertainty of those estimates.

If only marginal probabilities are known, do not multiply them without justification: a shared storage outage can make both outcomes fail. If neither candidate has evidence, report information content as unknown and propose a representative load/crash experiment. A preference based on lower operational complexity can still be stated, but it is not a measured information-content result.
