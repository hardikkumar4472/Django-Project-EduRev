import os
import re

template_dir = 'templates'
results = []

for root, dirs, files in os.walk(template_dir):
    for f in files:
        if f.endswith('.html'):
            filepath = os.path.join(root, f)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as fp:
                lines = fp.readlines()

            for i, line in enumerate(lines, 1):
                # Search for dark text colors
                match = re.search(r'<(h[1-6]|p|div|span|label)[^>]*style=["\'][^"\']*color:\s*(#[0-6][0-9a-fA-F]{5}|#000|#111|#222|#333|#444|#555|#666|var\(--navy-[0-9]+\))[^"\']*["\']', line, re.IGNORECASE)
                if match:
                    tag = match.group(1)
                    color = match.group(2)
                    results.append((filepath, i, tag, color, line.strip()[:140]))

print(f"Total lines with dark inline color: {len(results)}")
# Group by filepath
by_file = {}
for path, line_no, tag, color, text in results:
    by_file.setdefault(path, []).append((line_no, tag, color, text))

for path, items in sorted(by_file.items()):
    print(f"\n=== {path} ({len(items)} items) ===")
    for line_no, tag, color, text in items[:6]:
        print(f"  Line {line_no} [{tag}] {color}: {text}")
