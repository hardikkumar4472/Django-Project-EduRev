# Locking Strategy & Concurrency Safety Specification

## Phase 14 & Phase 18 Core Technical Foundation

In a university multi-party room exchange system, transactions operate over cycles of length 2, 3, 4, or 5:

```
Student A: Bed 101 → Bed 203
Student B: Bed 203 → Bed 304
Student C: Bed 304 → Bed 412
Student D: Bed 412 → Bed 101
```

A partial room transfer is a catastrophic failure mode in student accommodation: if Student A moves to Bed 203 and Student B moves to Bed 304, but Student C's transfer fails, Bed 101 becomes unassigned while Student D is left stranded without housing.

This document details how **CampusExchange** mathematically guarantees **Zero Partial Transfers** and **Zero ABBA Deadlocks**.

---

## 1. Why `select_for_update()` is Required

Standard relational database isolation levels (`READ COMMITTED`) allow non-repeatable reads and phantom reads across concurrent threads. If Warden Sharma approves Cycle 1 while Warden Verma approves Cycle 2 (both touching Bed 203), standard `UPDATE` statements without pessimistic locking can interleave:

1. Thread 1 reads Bed 203 (Occupant = Student B).
2. Thread 2 reads Bed 203 (Occupant = Student B).
3. Thread 1 updates Bed 203 (New Occupant = Student A).
4. Thread 2 updates Bed 203 (New Occupant = Student E).

This results in silent data corruption where Student A believes they own Bed 203, but Student E is recorded in the bed table.

By calling `Bed.objects.select_for_update().filter(...)` inside `transaction.atomic()`, the database engine acquires exclusive row-level locks on the selected physical rows until the transaction explicitly commits or rolls back.

---

## 2. Why Primary-Key Ordered Lock Acquisition Prevents ABBA Deadlocks

Consider two concurrent transactions attempting to acquire locks on two overlapping beds:

- **Transaction Alpha (TxA)** touches Bed 101 and Bed 203.
- **Transaction Beta (TxB)** touches Bed 203 and Bed 101.

If locks are acquired in arbitrary sequence:
- TxA locks Bed 101 and requests Bed 203.
- TxB locks Bed 203 and requests Bed 101.
- Both threads wait on each other indefinitely: **ABBA Deadlock**. The database engine must kill one transaction.

### The Algorithm:
To make deadlocks mathematically impossible, `occupancy_service.py` sorts all bed IDs in strictly ascending order:

```python
# Step 4 & 5: Collect and Sort All Affected Bed IDs
current_bed_ids = [p.current_bed_id for p in participants]
target_bed_ids = [p.target_bed_id for p in participants]
all_bed_ids = list(set(current_bed_ids + target_bed_ids))

# STRICT PRIMARY KEY ORDER:
sorted_bed_ids = sorted(all_bed_ids)

# Acquire exclusive row locks in uniform order:
locked_beds_qs = Bed.objects.select_for_update().filter(id__in=sorted_bed_ids)
```

Because all transactions always request locks in the same order (lowest integer ID first), a circular wait condition cannot form in the database dependency graph.

---

## 3. The 12-Step Atomic Execution Protocol

Every multi-party room exchange follows this strict protocol in `occupancy_service.py`:

```
 1. Enter transaction.atomic()
 2. Validate proposal status == READY_FOR_APPROVAL
 3. Validate 100% participant acceptance
 4. Collect all current and target Bed IDs
 5. Sort Bed IDs in ascending primary key order
 6. Execute Bed.objects.select_for_update() on sorted IDs
 7. Re-check occupancy integrity (verify current resident hasn't changed)
 8. Vacate all source beds
 9. Assign each student to target bed
10. Create immutable TransferRecord for each student
11. Update ExchangeProposal status to COMPLETED
12. Write detailed AuditEntry and Commit transaction
```

If **any** assertion or constraint fails at any point between Steps 1 and 12, the transaction executes an immediate rollback:
- All bed assignments revert to their original state.
- No partial room transfer is ever written to disk.
- An audit log documents the abort reason.

---

## 4. Concurrency Verification Test Suite

Our test suite in `tests/test_concurrency.py` tests this behavior using real Python multi-threading (`threading.Thread`) against `TransactionTestCase`:
1. **Test 1**: 4-party cyclic swap executes cleanly.
2. **Test 2**: One participant decline rolls back everything with zero occupancy change.
3. **Test 3**: Proposal expiration aborts transfer.
4. **Test 4**: Two simultaneous threads racing for overlapping beds result in 0 deadlocks and 0 partial allocations.
