import os, re

files = [
    'templates/exchange/student_dashboard.html',
    'templates/exchange/warden_dashboard.html',
    'templates/exchange/create_request.html',
    'templates/exchange/cycle_explorer.html',
    'templates/exchange/transfers_list.html',
    'templates/exchange/admin_policies.html',
    'templates/exchange/analytics_dashboard.html',
    'templates/accounts/admin_users_list.html',
    'templates/exchange/notifications_list.html',
    'templates/exchange/lifestyle_quiz.html',
    'templates/accounts/signup.html',
]

for f in files:
    if not os.path.exists(f): continue
    with open(f, 'r', encoding='utf-8') as fl:
        lines = fl.readlines()
    print(f"=== {f} ===")
    for i, line in enumerate(lines):
        # find any headings or p or div with color: #0f172a or color: #1e293b or color: #334155
        if re.search(r'<(h1|h2|h3|h4|p|div|section)[^>]*style="[^"]*color:\s*(#0f172a|#1e293b|#334155|var\(--navy-800\))', line, re.I):
            # check if it is outside card
            print(f"  Line {i+1}: {line.strip()[:100]}")
