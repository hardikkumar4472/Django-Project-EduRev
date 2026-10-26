"""
Script to generate a comprehensive, beginner-friendly, beautifully formatted PDF documentation
for the CampusExchange (EduRev Hostel Room Exchange Platform) project.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        # Don't draw headers/footers on cover page
        if self._pageNumber == 1:
            return

        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#4B5563"))

        # Running Header
        self.drawString(54, letter[1] - 36, "CampusExchange (EduRev) — Complete Project Documentation & Master Guide")
        self.setFont("Helvetica", 8)
        self.drawRightString(letter[0] - 54, letter[1] - 36, "University Hostel System")

        self.setStrokeColor(colors.HexColor("#E5E7EB"))
        self.setLineWidth(0.75)
        self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)

        # Running Footer
        self.line(54, 46, letter[0] - 54, 46)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#6B7280"))
        self.drawString(54, 32, "Confidential — For University Administration, Engineering & Operations")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 32, page_text)
        self.restoreState()


def build_pdf(filename="CampusExchange_Complete_Project_Documentation.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom Palettes
    primary_color = colors.HexColor("#1E3A8A")     # Royal Navy
    secondary_color = colors.HexColor("#0D9488")   # Teal
    accent_color = colors.HexColor("#D97706")      # Amber
    dark_neutral = colors.HexColor("#1F2937")      # Charcoal
    light_bg = colors.HexColor("#F9FAFB")          # Light grey
    callout_bg = colors.HexColor("#F0FDF4")        # Soft green
    callout_border = colors.HexColor("#10B981")

    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=26,
        leading=32,
        textColor=primary_color,
        alignment=0,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#4B5563"),
        alignment=0,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=primary_color,
        spaceBefore=16,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=secondary_color,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    h3_style = ParagraphStyle(
        'Heading3_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=dark_neutral,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=dark_neutral,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1E293B")
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    table_body_style = ParagraphStyle(
        'TableBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=dark_neutral
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#065F46")
    )

    story = []

    # ==========================================
    # COVER / HEADER BLOCK
    # ==========================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("CampusExchange — University Room Exchange Platform", title_style))
    story.append(Paragraph("Master Project Documentation, Architecture Specification & Zero-Knowledge System Guide", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=primary_color, spaceBefore=4, spaceAfter=14))

    # Meta Overview Box
    meta_data = [
        [
            Paragraph("<b>Target Audience:</b> Students, Wardens, Deans, Developers", table_body_style),
            Paragraph("<b>Tech Stack:</b> Python 5.x / Django / SQLite (ACID) / NetworkX", table_body_style)
        ],
        [
            Paragraph("<b>Core Invariant:</b> Zero Partial Room Transfers (Row Locks)", table_body_style),
            Paragraph("<b>Matching Engine:</b> Multi-Hop Cyclic Graph Traversal (DFS 2-5)", table_body_style)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[250, 250])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F3F4F6")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#D1D5DB")),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 14))

    # ==========================================
    # SECTION 1: EXECUTIVE SUMMARY (ZERO KNOWLEDGE)
    # ==========================================
    story.append(Paragraph("1. Executive Summary & The Problem It Solves", h1_style))
    story.append(Paragraph(
        "<b>What is this project?</b><br/>"
        "In university campuses, hundreds of students are allocated hostel rooms each semester. Frequently, roommates find themselves "
        "mismatched, situated far from classes, on an inconvenient floor, or wishing to live next to classmates. "
        "Traditionally, room changes require manual applications, bureaucratic paperwork, and chaotic student negotiation.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The Fundamental Challenge: Direct Swaps Are Rare!</b><br/>"
        "If <i>Student A</i> wants <i>Student B's</i> room, it is very unlikely that <i>Student B</i> also wants <i>Student A's</i> exact room. "
        "Instead, room preferences form <b>multi-party chains</b>:<br/>"
        "• <b>Student A</b> wants Room 203 (occupied by B)<br/>"
        "• <b>Student B</b> wants Room 304 (occupied by C)<br/>"
        "• <b>Student C</b> wants Room 412 (occupied by D)<br/>"
        "• <b>Student D</b> wants Room 101 (occupied by A)<br/>"
        "If all four students agree and the Warden approves, <b>everyone shifts one step forward simultaneously</b> and everyone gets their dream room!",
        body_style
    ))
    story.append(Paragraph(
        "<b>CampusExchange</b> automates this entire lifecycle: discovering multi-party cycles using graph theory algorithms, collecting unanimous "
        "student consensus, giving wardens a one-click atomic approval queue, and issuing verifiable QR-coded transfer passes.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # ==========================================
    # SECTION 2: END-TO-END 6-PHASE WORKFLOW
    # ==========================================
    story.append(Paragraph("2. The End-to-End Operational Lifecycle", h1_style))
    story.append(Paragraph(
        "A room change travels through 6 distinct, tamper-proof stages. No step can be bypassed.",
        body_style
    ))

    phases = [
        ("Phase 1: Student Registration & Inventory Allotment",
         "A student creates an account or logs in. The system checks their university enrollment ID, gender, and current bed allocation (e.g., Tagore Block A, Room 101, Bed 1)."),
        ("Phase 2: Submitting an Exchange Request",
         "The student specifies what they want: preferred hostel (e.g., Sarojini), preferred room type (Single, Double), floor preferences, or a specific desired room. Before accepting the request, the platform verifies fee clearances, absence of disciplinary holds, and cooldown intervals."),
        ("Phase 3: Bounded Cycle Discovery (The Math Engine)",
         "The system builds a directed graph of all students and their desired rooms. It automatically uncovers 2-party direct swaps, 3-party triangles, 4-party loops, and 5-party circular rotations."),
        ("Phase 4: Proposal Initiation & 100% Student Consensus",
         "When a student selects a discovered cycle, an official Proposal is drafted. Every student in the cycle receives a notification. All participants must vote 'Accept'. If even one person declines or the proposal times out, it is cleanly canceled."),
        ("Phase 5: Warden Review & Atomic Execution",
         "Once 100% consensus is achieved, the proposal reaches the Hostel Warden's queue. The Warden inspects student profiles, disciplinary notes, and room moves. With one click, the system acquires row-level database locks, atomically swaps all beds, and logs immutable audit trails."),
        ("Phase 6: Verifiable Transfer Pass & Key Handover",
         "Students receive an official Digital Transfer Pass with a cryptographic QR code. They present this pass to the Hostel Caretaker to return their old keys and collect keys to their new room.")
    ]

    for title, desc in phases:
        story.append(Paragraph(f"<b>{title}</b>", h3_style))
        story.append(Paragraph(desc, body_style))

    story.append(PageBreak())

    # ==========================================
    # SECTION 3: SYSTEM ARCHITECTURE & FILE TREE
    # ==========================================
    story.append(Paragraph("3. Complete Project Architecture & Directory Structure", h1_style))
    story.append(Paragraph(
        "CampusExchange is structured cleanly according to professional Django architectural best practices, dividing concerns into "
        "modular applications, specialized services, and isolated presentation layers.",
        body_style
    ))

    structure_data = [
        [Paragraph("<b>Directory / File</b>", table_header_style), Paragraph("<b>Classification</b>", table_header_style), Paragraph("<b>Function & How It Works</b>", table_header_style)],
        [
            Paragraph("<b>manage.py</b>", code_style),
            Paragraph("CLI Tool", table_body_style),
            Paragraph("Django command-line utility for database migrations, tests, and custom seed commands.", table_body_style)
        ],
        [
            Paragraph("<b>edurev_swap/</b>", code_style),
            Paragraph("Project Core", table_body_style),
            Paragraph("Global configuration directory containing <code>settings.py</code> (installed apps, DB, auth backends), <code>urls.py</code> (root URL routing), and <code>wsgi.py</code>.", table_body_style)
        ],
        [
            Paragraph("<b>accounts/</b>", code_style),
            Paragraph("Django App", table_body_style),
            Paragraph("Handles authentication, user identities, roles (Student, Warden, Chief Warden, Admin, Dean), and the instant Demo Persona Switcher.", table_body_style)
        ],
        [
            Paragraph("<b>hostel/</b>", code_style),
            Paragraph("Django App", table_body_style),
            Paragraph("Manages campus physical assets: Hostels, Blocks, Floors, Rooms, and Beds. Tracks which student is currently assigned to which bed.", table_body_style)
        ],
        [
            Paragraph("<b>exchange/</b>", code_style),
            Paragraph("Django App", table_body_style),
            Paragraph("Core engine orchestrating exchange requests, proposals, voting consensus, approvals, and official transfer passes.", table_body_style)
        ],
        [
            Paragraph("<b>exchange/services/</b>", code_style),
            Paragraph("Business Logic", table_body_style),
            Paragraph("Modular services layer decoupling business rules from HTTP views (matching engine, occupancy locks, eligibility, audit).", table_body_style)
        ],
        [
            Paragraph("<b>templates/</b>", code_style),
            Paragraph("UI Layer", table_body_style),
            Paragraph("Jinja2/Django HTML templates including student cockpit, warden approvals, cycle explorer, and transfer certificates.", table_body_style)
        ],
        [
            Paragraph("<b>static/</b>", code_style),
            Paragraph("Frontend Assets", table_body_style),
            Paragraph("CSS stylesheets, interactive JS graph rendering scripts, and campus visual media.", table_body_style)
        ],
        [
            Paragraph("<b>tests/</b>", code_style),
            Paragraph("QA / Verification", table_body_style),
            Paragraph("Automated test suite, including multi-threaded race-condition and concurrency safety tests.", table_body_style)
        ],
    ]

    t_struct = Table(structure_data, colWidths=[120, 80, 300])
    t_struct.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_struct)
    story.append(Spacer(1, 10))

    # ==========================================
    # SECTION 4: DEEP DIVE INTO EACH MODULE
    # ==========================================
    story.append(Paragraph("4. Deep Dive: What Every Component Does", h1_style))

    story.append(Paragraph("A. The <code>accounts</code> Application (User Management & RBAC)", h2_style))
    story.append(Paragraph(
        "• <b>Custom User Model (<code>models.py</code>):</b> Extends Django's base user to include University Roll Number, Gender (crucial for hostel segregation), "
        "Academic Year/Batch, Disciplinary Status, and Fee Clearance flags.<br/>"
        "• <b>Universal Auth Backend (<code>backends.py</code>):</b> Allows students and faculty to log in seamlessly with either Username, Email address, or University ID.<br/>"
        "• <b>Role-Based Access Control (<code>middleware.py</code> & <code>context_processors.py</code>):</b> Dynamically regulates endpoint access. "
        "Students cannot view warden approvals; wardens cannot alter admin policies. Exposes an instant 1-click <b>Demo Persona Switcher</b> in the top navbar.<br/>"
        "• <b>Management Seeder (<code>management/commands/seed_demo.py</code>):</b> Pre-configures realistic accounts for Aarav, Bhavya, Chirag, Divya, Warden Sharma, and Dean Rao.",
        body_style
    ))

    story.append(Paragraph("B. The <code>hostel</code> Application (Campus Physical Hierarchy)", h2_style))
    story.append(Paragraph(
        "Represents university physical housing as a relational hierarchy:<br/>"
        "<b>Hostel</b> (e.g., Tagore Boys Hostel) ➔ <b>Block</b> (Block A) ➔ <b>Floor</b> (1st Floor) ➔ <b>Room</b> (Room 101) ➔ <b>Bed</b> (Bed 1).<br/>"
        "• <b>Bed Model:</b> Holds a foreign key to <code>current_occupant</code>. Every bed has an occupancy status (OCCUPIED, VACANT, UNDER_MAINTENANCE).<br/>"
        "• <b>Services:</b> Provides real-time floor plans, room capacity metrics, and vacancy calculations.",
        body_style
    ))

    story.append(Paragraph("C. The <code>exchange</code> Application & Services Layer", h2_style))
    story.append(Paragraph(
        "This is the heart of the system, comprising 6 dedicated service modules:",
        body_style
    ))

    services_data = [
        [Paragraph("<b>Service Module</b>", table_header_style), Paragraph("<b>Technical Functionality & Algorithms</b>", table_header_style)],
        [
            Paragraph("<b>Matching Engine</b><br/><code>matching_service.py</code>", code_style),
            Paragraph("Constructs a <b>Directed Graph (DiGraph)</b> where students are nodes and edges represent acceptable room matches. "
                      "Uses <b>NetworkX</b> cycle detection to discover bounded cycles of length 2 to 5. Implements score normalization and rotational deduplication "
                      "(e.g., [A,B,C] == [B,C,A]).", table_body_style)
        ],
        [
            Paragraph("<b>Occupancy Engine</b><br/><code>occupancy_service.py</code>", code_style),
            Paragraph("Guarantees <b>ACID transactional safety</b>. When Warden signs off on a swap, this engine sorts Bed Primary Keys in ascending order, "
                      "acquires row-level locks via <code>select_for_update()</code>, verifies bed occupancy, rotates all occupants atomically, and releases locks.", table_body_style)
        ],
        [
            Paragraph("<b>Eligibility Service</b><br/><code>eligibility_service.py</code>", code_style),
            Paragraph("Enforces university bylaws: checks fee dues, disciplinary holds, cooling-off waiting periods between transfers, and gender policy compatibility.", table_body_style)
        ],
        [
            Paragraph("<b>Proposal Service</b><br/><code>proposal_service.py</code>", code_style),
            Paragraph("Tracks the lifecycle of multi-party proposals: creates participant voter ballots, tracks unanimous acceptance countdowns, and handles automatic expiration.", table_body_style)
        ],
        [
            Paragraph("<b>Audit Service</b><br/><code>audit_service.py</code>", code_style),
            Paragraph("Writes append-only, tamper-proof audit records capturing actor IP, timestamp, previous bed, new bed, and approval authority for administrative transparency.", table_body_style)
        ],
        [
            Paragraph("<b>Notification Service</b><br/><code>notification_service.py</code>", code_style),
            Paragraph("Dispatches alerts to student cockpits when proposals are initiated, accepted, rejected, or completed.", table_body_style)
        ]
    ]

    t_serv = Table(services_data, colWidths=[150, 350])
    t_serv.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), secondary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_serv)

    story.append(PageBreak())

    # ==========================================
    # SECTION 5: ADVANCED TECHNICAL CONCEPTS EXPLAINED
    # ==========================================
    story.append(Paragraph("5. Advanced Engineering Concepts Explained Simply", h1_style))

    story.append(Paragraph("A. Graph Cycle Discovery (How Does the System Find Swaps?)", h2_style))
    story.append(Paragraph(
        "Think of each student as a person holding a key. A directed arrow means: <i>'I want the key held by that person'</i>.<br/>"
        "• <b>2-Party Cycle:</b> Student A wants B's key; Student B wants A's key. (A ➔ B ➔ A)<br/>"
        "• <b>4-Party Rotation:</b> Student A wants B's key; B wants C's; C wants D's; D wants A's. (A ➔ B ➔ C ➔ D ➔ A)<br/>"
        "The system executes a bounded depth-first search (DFS) through NetworkX. To ensure usability, cycles are capped at 5 participants.",
        body_style
    ))

    story.append(Spacer(1, 4))
    story.append(Paragraph("B. Concurrency, Race Conditions & Deadlock Immunity", h2_style))
    story.append(Paragraph(
        "Imagine two proposals are pending at the same moment: Proposal X involves Beds 10 and 20; Proposal Y also involves Bed 20 and Bed 35. "
        "If two wardens hit 'Approve' at the exact same millisecond, what happens?",
        body_style
    ))

    danger_data = [
        [
            Paragraph("<b>The Risk Without This Engine</b>", ParagraphStyle('WarnH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#B91C1C"))),
            Paragraph("<b>How CampusExchange Prevents It</b>", ParagraphStyle('SafeH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#047857")))
        ],
        [
            Paragraph("<b>Split / Partial Transfer:</b> Student A moves into Bed 20, but Bed 20's original occupant fails to move into Bed 35, leaving two students in one bed!", table_body_style),
            Paragraph("<b>Atomic All-or-Nothing:</b> Wrapped in <code>transaction.atomic()</code>. Either 100% of students move, or the entire transaction aborts with zero changes.", table_body_style)
        ],
        [
            Paragraph("<b>ABBA Deadlock:</b> Transaction 1 locks Bed 10 and waits for Bed 20. Transaction 2 locks Bed 20 and waits for Bed 10. The database freezes forever!", table_body_style),
            Paragraph("<b>Ascending Primary-Key Ordering:</b> Every transaction sorts Bed IDs (e.g., Bed 10 then Bed 20) before acquiring locks via <code>select_for_update()</code>. Deadlocks are mathematically impossible.", table_body_style)
        ]
    ]
    t_danger = Table(danger_data, colWidths=[250, 250])
    t_danger.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#FEF2F2")),
        ('BACKGROUND', (1,0), (1,-1), colors.HexColor("#ECFDF5")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_danger)
    story.append(Spacer(1, 10))

    # ==========================================
    # SECTION 6: USER ROLES (RBAC) & PERMISSIONS
    # ==========================================
    story.append(Paragraph("6. User Personas & Role Permissions Matrix", h1_style))
    story.append(Paragraph(
        "CampusExchange enforces clear separation of authority across university administrative tiers:",
        body_style
    ))

    rbac_table = [
        [Paragraph("<b>Permission / Action</b>", table_header_style), Paragraph("<b>Student</b>", table_header_style), Paragraph("<b>Warden</b>", table_header_style), Paragraph("<b>Chief Warden</b>", table_header_style), Paragraph("<b>Dean / Admin</b>", table_header_style)],
        [Paragraph("View Room Cutaway & Allocation", table_body_style), Paragraph("Own Only", table_body_style), Paragraph("Hostel Level", table_body_style), Paragraph("All Hostels", table_body_style), Paragraph("All Hostels", table_body_style)],
        [Paragraph("Submit Exchange Request", table_body_style), Paragraph("Yes", table_body_style), Paragraph("No", table_body_style), Paragraph("No", table_body_style), Paragraph("No", table_body_style)],
        [Paragraph("Discover & Vote on Proposals", table_body_style), Paragraph("Yes", table_body_style), Paragraph("No", table_body_style), Paragraph("No", table_body_style), Paragraph("No", table_body_style)],
        [Paragraph("Review & Approve Same-Hostel Swaps", table_body_style), Paragraph("No", table_body_style), Paragraph("Yes", table_body_style), Paragraph("Yes", table_body_style), Paragraph("Yes", table_body_style)],
        [Paragraph("Review Cross-Hostel Swaps", table_body_style), Paragraph("No", table_body_style), Paragraph("No", table_body_style), Paragraph("Yes", table_body_style), Paragraph("Yes", table_body_style)],
        [Paragraph("Download Official QR Transfer Pass", table_body_style), Paragraph("Own Pass", table_body_style), Paragraph("Verify Any", table_body_style), Paragraph("Verify Any", table_body_style), Paragraph("Verify Any", table_body_style)],
        [Paragraph("Campus Analytics & Audit Logs", table_body_style), Paragraph("No", table_body_style), Paragraph("No", table_body_style), Paragraph("No", table_body_style), Paragraph("Full Access", table_body_style)],
    ]
    t_rbac = Table(rbac_table, colWidths=[180, 75, 80, 85, 80])
    t_rbac.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_rbac)
    story.append(PageBreak())

    # ==========================================
    # SECTION 7: STEP-BY-STEP GETTING STARTED
    # ==========================================
    story.append(Paragraph("7. Setup, Testing & Verification Guide", h1_style))
    story.append(Paragraph(
        "Follow these steps to set up, populate, and test the entire platform on a local machine:",
        body_style
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>Step 1: Install Dependencies & Run Migrations</b>", h3_style))
    story.append(Paragraph(
        "<code>pip install -r requirements.txt</code><br/>"
        "<code>python manage.py makemigrations accounts hostel exchange</code><br/>"
        "<code>python manage.py migrate</code>",
        body_style
    ))
    story.append(Paragraph("<b>Step 2: Seed Realistic Campus Demo Data</b>", h3_style))
    story.append(Paragraph(
        "<code>python manage.py seed_demo</code><br/>"
        "Populates 4 Hostels (Tagore, Sarojini, Aryabhatta, Gargi), 120+ rooms, 240+ beds, demo students (Aarav, Bhavya, Chirag, Divya), wardens, and a ready-to-test 4-party swap cycle (Default password: <code>campus123</code>).",
        body_style
    ))
    story.append(Paragraph("<b>Step 3: Run Dev Server & Switch Personas</b>", h3_style))
    story.append(Paragraph(
        "<code>python manage.py runserver</code> ➔ Visit <code>http://127.0.0.1:8000/</code>.<br/>"
        "Use the top navigation <b>Persona Switcher</b> to instantly jump between Student, Warden, and Admin roles.",
        body_style
    ))
    story.append(Paragraph("<b>Step 4: Run Automated Concurrency Suite</b>", h3_style))
    story.append(Paragraph(
        "<code>python manage.py test tests</code> ➔ Tests multi-threaded atomic row-locking under parallel approval stress.",
        body_style
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF documentation: {filename}")

if __name__ == "__main__":
    build_pdf()

