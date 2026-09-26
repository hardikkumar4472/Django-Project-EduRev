# CampusExchange — University Hostel Room Exchange & Multi-Party Swap Platform

Official university platform for post-allocation hostel room exchanges, built strictly according to the **P04 Master Build Specification**.

---

## 🌟 Key Pillars & Features

1. **Multi-Party Graph Cycle Matching**: Discovers 2-party direct swaps and 3, 4, and 5-party multi-hop rotations (`A → B → C → D → A`).
2. **Deterministic Row-Level Locking**: Employs `transaction.atomic()` with primary-key sorted `select_for_update()` on all affected beds, mathematically guaranteeing **zero partial room transfers**.
3. **Deadlock Immunity**: Ascending primary-key order lock acquisition prevents ABBA deadlocks during concurrent multi-warden approvals.
4. **All-or-Nothing Consensus**: Every participant must accept before a proposal enters the warden review queue.
5. **No Left-Hand Tool Panel / Sidebar**: Clean, spacious full-width top navigation bar dynamically driven by **Role-Based Access Control (RBAC)**.
6. **Instant Persona Switcher**: Seamlessly toggle between Student, Warden, Chief Warden, Admin, and Dean of Student Welfare (DSW).
7. **Official Transfer Pass Generation**: Digitally verifiable transfer letter with generated QR code for caretaker key handover.

---

## 🚀 Quickstart Guide

### 1. Initialize Database Migrations
```bash
python manage.py makemigrations accounts hostel exchange
python manage.py migrate
```

### 2. Seed Realistic University Demo Data
```bash
python manage.py seed_demo
```
This automatically seeds:
- 4 Hostels (Tagore, Sarojini, Aryabhatta, Gargi)
- 120+ Rooms, 240+ Beds
- 50+ Students, 2 Wardens, 1 Chief Warden, 1 Admin, 1 Dean
- The signature 4-party rotation scenario (`A → B-203 → C-304 → D-412 → A-101`)

### 3. Run Development Server
```bash
python manage.py runserver
```
Access the platform at: `http://127.0.0.1:8000/`

---

## 👥 Demo Accounts (Default Password: `campus123`)

| Username | Name | Role | Starting Room Allocation |
| :--- | :--- | :--- | :--- |
| `student_a` | Aarav Sharma | Student | Tagore Block A, Room 101 |
| `student_b` | Bhavya Patel | Student | Tagore Block B, Room 203 |
| `student_c` | Chirag Verma | Student | Tagore Block C, Room 304 |
| `student_d` | Divya Nair | Student | Tagore Block D, Room 412 |
| `warden_sharma` | Dr. K. Sharma | Warden | Tagore / Sarojini Warden |
| `chief_warden_verma` | Prof. R. Verma | Chief Warden | Campus Chief Warden |
| `admin_patel` | S. Patel | Administrator | Housing Policy Admin |
| `dean_rao` | Prof. M. Rao | Dean (DSW) | Dean of Student Welfare |

*Tip: Use the **Demo Persona** dropdown in the top navbar to switch roles in 1 click without re-typing passwords.*

---

## 🧪 Running Automated Tests

Run the test suite (including multi-threaded concurrency race condition testing):
```bash
python manage.py test tests
```
