# System Architecture & Complete Workflow Guide

**Project:** CampusExchange (EduRev Hostel Room Exchange Platform)  
**Framework:** Django 5.x / Python / SQLite (ACID)  
**Graph Engine:** NetworkX Directed Graph Cycle Detection  
**Security & Concurrency:** Pessimistic Row-Level Locking (`select_for_update`) with Deterministic PK Ordering  

---

## Table of Contents
1. [High-Level System Architecture](#1-high-level-system-architecture)
2. [End-to-End Operational Lifecycle Workflow](#2-end-to-end-operational-lifecycle-workflow)
3. [Graph Matching Engine Architecture](#3-graph-matching-engine-architecture)
4. [Atomic Concurrency & Two-Phase Locking Strategy](#4-atomic-concurrency--two-phase-locking-strategy)
5. [Entity Relationship Diagram (ERD)](#5-entity-relationship-diagram-erd)
6. [Role-Based Access Control (RBAC) Matrix](#6-role-based-access-control-rbac-matrix)

---

## 1. High-Level System Architecture

The application follows a clean 4-tier layered architecture enforcing clear separation of concerns, transactional integrity, and policy compliance.

```mermaid
flowchart TB
    subgraph Client_Layer["🖥️ Presentation & Client Tier"]
        UI_Guest["Public Pages<br/>(Landing, Sign In, Registration)"]
        UI_Student["Student Cockpit<br/>(Room Visualizer, Match Finder, Proposals)"]
        UI_Warden["Warden Console<br/>(Consensus Queue, Review & Execute)"]
        UI_Admin["DSW / Admin Dashboard<br/>(Analytics, Policies, Audit Logs)"]
    end

    subgraph Security_Layer["🛡️ Security & Access Control Tier"]
        AuthMiddleware["Django Authentication"]
        RBAC["RBAC Middleware<br/>(Role-Based Route Guards)"]
        ContextProc["RBAC Context Processor<br/>(Dynamic UI Roles & Bed Data)"]
    end

    subgraph Engine_Layer["⚙️ Core Business Logic & Engines Tier"]
        EligibilitySvc["Eligibility Service<br/>(Fee Clearance, Disciplinary Checks, Cooling-off)"]
        MatchingEngine["Graph Matching Engine<br/>(NetworkX DiGraph, 2 to 5 Cycle Finder)"]
        ProposalSvc["Proposal Management Service<br/>(Consensus Tracker, Expiry Countdown)"]
        OccupancyEngine["Atomic Occupancy Engine<br/>(Ascending PK Row Locks, Multi-Bed Swap)"]
        AuditSvc["Audit Service<br/>(Append-Only Immutable Event Logging)"]
        QRGenerator["Cryptographic QR Engine<br/>(Base64 Security Token & Pass Generation)"]
    end

    subgraph Database_Layer["💾 Relational Persistence Tier (ACID)"]
        DB_Users[("User Accounts & Roles")]
        DB_Hostel[("Hostels, Blocks, Rooms, Beds")]
        DB_Exchange[("Requests, Proposals, Participants")]
        DB_Transfers[("Transfer Records & QR Tokens")]
        DB_Audit[("Audit Log Entries")]
    end

    Client_Layer --> Security_Layer
    Security_Layer --> Engine_Layer
    Engine_Layer --> Database_Layer
```

---

## 2. End-to-End Operational Lifecycle Workflow

The entire lifecycle of a room exchange—from student registration through to warden sign-off and move-in pass generation:

```mermaid
sequenceDiagram
    autonumber
    actor S1 as Student A
    actor S2 as Student B
    actor S3 as Student C
    participant Web as Web / Portal
    participant Engine as Graph Matching Engine
    participant Prop as Proposal Service
    actor W as Hostel Warden
    participant Lock as Atomic Occupancy Engine
    participant DB as Database (SQLite/PostgreSQL)

    Note over S1, DB: Phase 1: Registration & Initial Allotment
    S1->>Web: Register Student Account (Roll ID, Gender, Credentials)
    S1->>Web: Claim / Receive Vacant Bed (e.g., Room A-101, Bed 1)
    Web->>DB: User created & Bed.current_occupant set

    Note over S1, DB: Phase 2: Exchange Request Activation
    S1->>Web: Submit Exchange Request (Preferences: Hostel, Floor, Room Type)
    Web->>DB: Validate Eligibility (Fees=Clear, Hold=None, Cooldown=OK)
    Web->>DB: Save ExchangeRequest (Status: ACTIVE)

    Note over Engine, DB: Phase 3: Bounded Cycle Discovery
    S1->>Web: Navigate to Matches (/matches/)
    Web->>Engine: find_cycles(target_student_id=Student A)
    Engine->>DB: Fetch Active Requests & Current Bed Allocations
    Engine->>Engine: Build Directed Graph & Detect Cycles (Lengths 2 to 5)
    Engine-->>Web: Discovered Valid Cycles (e.g., A ➔ B ➔ C ➔ A)

    Note over S1, Prop: Phase 4: Proposal Initiation & Voting
    S1->>Web: Click "Initiate Official Proposal"
    Web->>Prop: create_proposal_from_match()
    Prop->>DB: Create ExchangeProposal & ProposalParticipants (Status: PENDING)
    Prop->>Web: Notify Student B and Student C
    S1->>Web: Vote "Accept Proposal"
    S2->>Web: Vote "Accept Proposal"
    S3->>Web: Vote "Accept Proposal"
    Prop->>DB: 100% Consensus Reached! Transition Proposal to READY_FOR_APPROVAL

    Note over W, Lock: Phase 5: Warden Administrative Review & Atomic Execution
    W->>Web: Open Approval Queue (/warden/approvals/)
    W->>Web: Review Movement Chain & Enter Approval Remarks
    W->>Lock: Execute Atomic Transfer
    Lock->>DB: Sort Bed PKs Ascending [e.g., Bed 4, Bed 18, Bed 42]
    Lock->>DB: Acquire Pessimistic Locks: Bed.objects.select_for_update()
    Lock->>DB: Validate all beds still held by participants
    Lock->>DB: Rotate Bed.current_occupant atomically
    Lock->>DB: Create TransferRecord for each student with Verification Token
    Lock->>DB: Close ExchangeRequests (Status: COMPLETED)
    Lock->>DB: Commit Transaction & Log Audit Entries

    Note over S1, Web: Phase 6: Move-in Pass & Verification
    S1->>Web: View Transfers (/transfers/)
    Web-->>S1: Official Printable Certificate with Base64 QR Code
    S1->>W: Present QR Pass to Hostel Caretaker for Key Handover
```

---

## 3. Graph Matching Engine Architecture

The platform uses a directed dependency graph model where students with active requests represent nodes, and directed edges represent desirable room matches.

```mermaid
graph LR
    subgraph Direct_Swap["2-Party Direct Swap"]
        A1["Student A<br/>Room A-101"] -->|Desires B-203| B1["Student B<br/>Room B-203"]
        B1 -->|Desires A-101| A1
    end

    subgraph Multi_Party_Cycle["3-Party Multi-Hop Rotation Cycle"]
        A2["Student A<br/>Tagore A-101"] -->|Desires B-203| B2["Student B<br/>Tagore B-203"]
        B2 -->|Desires C-304| C2["Student C<br/>Sarojini C-304"]
        C2 -->|Desires A-101| A2
    end
```

### Edge Compatibility Scoring Algorithm
When evaluating if an edge exists from Student $A$ to Student $B$:
1. **Gender Residency Policy**: Strict separation (Boys hostel $\leftrightarrow$ Girls hostel blocked unless policy permits).
2. **Target Matching Criteria**:
   - Specific Room Request: $+50$ points (Exact match)
   - Preferred Hostel: $+25$ points
   - Preferred Room Type (Single / Double / Quad): $+15$ points
   - Preferred Floor: $+10$ points
3. **Cycle Filtering & Deduplication**:
   - Maximum Chain Length: Bounded between $2$ and $5$ students (configured in `PolicyRule`).
   - Rotational Invariance: `[A, B, C]` and `[B, C, A]` are normalized to minimal student ID to avoid duplicate proposals.

---

## 4. Atomic Concurrency & Two-Phase Locking Strategy

To prevent race conditions, double-allocations, and **ABBA Deadlocks** when multiple proposals share overlapping beds:

```mermaid
flowchart TD
    Start["Warden Approves Proposal"] --> FetchBeds["Collect all Bed IDs in Proposal Chain"]
    FetchBeds --> SortPKs["Sort Bed IDs in Ascending Primary Key Order<br/>e.g., Bed 3, Bed 12, Bed 45"]
    SortPKs --> BeginTx["Begin atomic database transaction: transaction.atomic()"]
    BeginTx --> RowLock["Acquire Row-Level Pessimistic Locks:<br/>Bed.objects.select_for_update().filter(id__in=sorted_ids)"]
    
    RowLock --> Verify["Verify State Consistency:<br/>1. Is every bed still occupied by expected student?<br/>2. Has any bed been reassigned or locked?"]
    
    Verify -- State Invalid --> Rollback["Abort & Raise OccupancyTransferError<br/>Rollback Transaction cleanly (Zero Partial Moves)"]
    
    Verify -- State Valid --> RotateOccupants["Simultaneously Rotate Bed.current_occupant<br/>Student A ➔ Bed B<br/>Student B ➔ Bed C<br/>Student C ➔ Bed A"]
    
    RotateOccupants --> GenRecords["Generate TransferRecord & Verification Tokens"]
    GenRecords --> CloseRequests["Mark ExchangeRequests as COMPLETED"]
    CloseRequests --> WriteAudit["Record Immutable AuditEntry"]
    WriteAudit --> Commit["Commit Transaction & Release Row Locks"]
    Commit --> Done["Dispatch QR Codes to Students"]
```

> **Deadlock Prevention Proof**: Because all concurrent warden transactions acquire row locks in the exact same sorted order (`Bed 3 -> Bed 12 -> Bed 45`), a circular wait state is mathematically impossible.

---

## 5. Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    Hostel ||--o{ Block : contains
    Block ||--o{ Room : contains
    Room ||--o{ Bed : houses
    User ||--o| Bed : "currently occupies"

    User ||--o{ ExchangeRequest : submits
    Bed ||--o{ ExchangeRequest : "current allocation"
    Room ||--o{ ExchangeRequest : "optional target"

    ExchangeProposal ||--o{ ProposalParticipant : includes
    User ||--o{ ProposalParticipant : participates
    Bed ||--o{ ProposalParticipant : "source bed"
    Bed ||--o{ ProposalParticipant : "destination bed"

    ExchangeProposal ||--o{ Approval : receives
    User ||--o{ Approval : "reviewed by"

    ExchangeProposal ||--o{ TransferRecord : produces
    User ||--o{ TransferRecord : "issued to"
    User ||--o{ AuditEntry : "action actor"

    Hostel {
        int id PK
        string name
        string code
        string gender_type
        boolean is_active
    }

    Room {
        int id PK
        string room_number
        int floor
        string room_type
        int capacity
    }

    Bed {
        int id PK
        string bed_number
        string occupancy_status
        int current_occupant_id FK
    }

    User {
        int id PK
        string username
        string university_id
        string role
        string gender
        boolean has_fee_clearance
        boolean has_disciplinary_hold
    }

    ExchangeRequest {
        int id PK
        string status
        string preferred_room_type
        int preferred_floor
        datetime created_at
    }

    ExchangeProposal {
        int id PK
        string proposal_code
        string proposal_type
        string status
        datetime expires_at
    }

    ProposalParticipant {
        int id PK
        string response
        datetime responded_at
    }

    TransferRecord {
        int id PK
        string transfer_code
        string verification_token
        datetime completed_at
    }
```

---

## 6. Role-Based Access Control (RBAC) Matrix

| Endpoint / Feature | Student | Hostel Warden | Chief Warden | Admin | Dean of Student Welfare (DSW) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Landing Page & System Stats** | ✅ View | ✅ View | ✅ View | ✅ View | ✅ View |
| **Student Cockpit & 2D Room Cutaway** | ✅ Own Room | ❌ | ❌ | ❌ | ❌ |
| **Submit Exchange Request** | ✅ Own | ❌ | ❌ | ❌ | ❌ |
| **View Graph Matches** | ✅ Own Matches | ❌ | ❌ | ❌ | ❌ |
| **Vote on Proposal (Accept/Decline)** | ✅ Participant | ❌ | ❌ | ❌ | ❌ |
| **Warden Approval Queue** | ❌ | ✅ Hostel | ✅ All Hostels | ✅ All | ❌ (Read Only) |
| **Execute Atomic Transfer** | ❌ | ✅ Intra-Hostel | ✅ Cross-Hostel | ✅ Override | ❌ |
| **Download Official Pass & QR Code** | ✅ Own Pass | ✅ Verify | ✅ Verify | ✅ Verify | ✅ Verify |
| **DSW Analytics & Real-Time Trends** | ❌ | ❌ | ❌ | ✅ Full | ✅ Full Read |
| **Policy Configuration (Cooldown, Length)**| ❌ | ❌ | ❌ | ✅ Configure | ❌ |
| **Audit Trail Inspection** | ❌ | ❌ | ❌ | ✅ Full Log | ✅ Full Log |
