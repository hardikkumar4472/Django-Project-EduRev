import os, re

files_to_check = [
    'templates/hostel/hostels_list.html',
    'templates/exchange/student_dashboard.html',
    'templates/exchange/warden_dashboard.html',
    'templates/exchange/how_it_works.html',
    'templates/exchange/guidelines.html',
    'templates/exchange/support.html',
    'templates/exchange/create_request.html',
    'templates/exchange/cycle_explorer.html',
    'templates/exchange/transfers_list.html',
    'templates/exchange/admin_policies.html',
    'templates/exchange/analytics_dashboard.html',
    'templates/accounts/admin_users_list.html',
]

print("Checking templates for potential color clash...")

for fpath in files_to_check:
    if not os.path.exists(fpath): continue
    with open(fpath, 'r', encoding='utf-8') as f:
        c = f.read()
    # Check if there are elements with dark color outside cards, or light color inside cards
    # Search for inline styles with color: #FFFFFF or color: white or color: #0F172A
    print(f"=== {fpath} ===")
    inline_colors = re.findall(r'style="[^"]*color:\s*([^;"]+)[^"]*"', c)
    color_counts = {}
    for clr in inline_colors:
        clr = clr.strip().lower()
        color_counts[clr] = color_counts.get(clr, 0) + 1
    for clr, cnt in sorted(color_counts.items(), key=lambda x: -x[1])[:6]:
        print(f"  {clr}: {cnt}")
