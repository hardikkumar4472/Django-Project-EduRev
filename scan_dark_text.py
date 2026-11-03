import os, re

fullpage_templates = [
    'templates/exchange/how_it_works.html',
    'templates/exchange/guidelines.html',
    'templates/exchange/support.html',
    'templates/hostel/hostels_list.html',
    'templates/exchange/student_dashboard.html',
    'templates/exchange/warden_dashboard.html',
    'templates/exchange/create_request.html',
    'templates/exchange/cycle_explorer.html',
    'templates/exchange/transfers_list.html',
    'templates/exchange/admin_policies.html',
    'templates/exchange/analytics_dashboard.html',
    'templates/accounts/admin_users_list.html',
    'templates/exchange/notifications_list.html',
    'templates/accounts/signup.html',
    'templates/exchange/lifestyle_quiz.html',
]

dark_colors = ['#0f172a', '#1e293b', '#334155', '#64748b', '#475569', 'var(--navy-800)', 'var(--text-primary)', 'var(--text-secondary)']

print("Scanning for dark text directly outside cards in fullpage-bg pages...")

for fpath in fullpage_templates:
    if not os.path.exists(fpath): continue
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find h1, h2, h3, p with dark colors outside cards
    lines = content.splitlines()
    in_card = False
    card_depth = 0
    issues = []
    
    for i, line in enumerate(lines):
        if 'class="card' in line or "class='card" in line or 'background: #ffffff' in line.lower() or 'background:#ffffff' in line.lower() or 'background: #f8fafc' in line.lower():
            in_card = True
        
        # Check if line has a dark color outside card
        for dc in dark_colors:
            if dc in line.lower():
                # check if this line is a heading or p directly on the page
                if ('<h1' in line or '<h2' in line or '<h3' in line or '<p' in line or '<span' in line) and not in_card:
                    issues.append((i+1, dc, line.strip()[:100]))
                    
        if in_card and ('</section>' in line or '</section' in line or '</div>' in line):
            # very rough reset
            pass
            
    print(f"=== {fpath} ===")
    for lno, dc, text in issues[:10]:
        print(f"  Line {lno} [{dc}]: {text}")
