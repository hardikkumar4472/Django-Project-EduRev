# System Architecture & Technical Specifications

## CampusExchange — P04 Master System

CampusExchange is an official university housing post-allocation room swap platform designed to replace informal messaging group swaps with an auditable, deterministic, multi-party exchange platform.

> 📖 **Full Visual Architecture & Workflow Specification:** See [ARCHITECTURE_WORKFLOW.md](file:///z:/7th%20Sem/Django/EDUREV%20project/ARCHITECTURE_WORKFLOW.md) for complete Mermaid sequence diagrams, graph matching flowchart, locking strategy, and ERD.

---

## 1. Domain Entities & Relationships

```
Hostel (1) ──< Block (N) ──< Room (N) ──< Bed (N) ──< [1-to-1] User (Student)
                                            │
                                            ▼
                           ExchangeRequest (1) ──< ProposalParticipant (N)
                                                         │
                                                         ▼
                                                ExchangeProposal (1)
                                                         │
                                                         ▼
                                                TransferRecord (N)
```

- **Hostel / Block / Room / Bed**: Physical university residence hierarchy.
- **User (Role-Based Access Control)**:
  - `STUDENT`: Creates requests, reviews matches, accepts/declines proposals, prints transfer pass.
  - `WARDEN`: Reviews intra-hostel proposals, executes atomic approvals.
  - `CHIEF_WARDEN`: Reviews and executes cross-hostel proposals.
  - `ADMIN`: Configures university policy rules (cooling-off period, chain lengths, fee requirements).
  - `DSW`: Dean of Student Welfare with read-only analytics, occupancy trends, and complete audit visibility.
- **ExchangeProposal & ProposalParticipant**: Represents a directed graph cycle where participants rotate allocations simultaneously.
- **TransferRecord**: Immutable proof of completed room reallocation containing a cryptographically verifiable token and QR code.
- **AuditEntry**: Append-only log of every state transition.

---

## 2. The 4 Technical Differentiators

1. **Bounded Graph Matching (Lengths 2 to 5)**:
   Discovers cycles via NetworkX directed graph depth-first search. Bounded traversal ensures sub-second response times across 2,000+ open requests without computational explosion.

2. **Row-Level Transactional Locking**:
   Enforces `Bed.objects.select_for_update()` inside `transaction.atomic()` ensuring that all rotations are all-or-nothing (zero partial room movements).

3. **Deterministic Lock Ordering (Zero ABBA Deadlocks)**:
   All affected bed primary keys are sorted ascending prior to lock acquisition, preventing cyclic wait states during concurrent warden approvals.

4. **100% Student Consensus Requirement**:
   Proposals only become eligible for administrative approval when every participating resident has explicitly voted to accept the rotation.
