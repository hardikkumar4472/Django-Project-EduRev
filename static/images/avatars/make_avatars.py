# Script to generate stylish SVG avatars
import os

avatars = [
    ("avatar_hardik.svg", "Hardik Kumar", "#1E3A8A", "#93C5FD", "HK"),
    ("avatar_aarav.svg", "Aarav Sharma", "#0D9488", "#99F6E4", "AS"),
    ("avatar_riya.svg", "Riya Sharma", "#BE185D", "#FBCFE8", "RS"),
    ("avatar_karan.svg", "Karan Patel", "#C2410C", "#FED7AA", "KP"),
    ("avatar_sneha.svg", "Sneha Verma", "#7C3AED", "#DDD6FE", "SV"),
    ("avatar_warden.svg", "Warden Sharma", "#0F766E", "#CCFBF1", "WS"),
    ("avatar_dean.svg", "Dean BSW", "#1E293B", "#CBD5E1", "DS"),
    ("avatar_arjun.svg", "Arjun Mehta", "#0369A1", "#BAE6FD", "AM"),
    ("avatar_nikhil.svg", "Nikhil Singh", "#4338CA", "#C7D2FE", "NS"),
    ("avatar_aman.svg", "Aman", "#059669", "#A7F3D0", "AM"),
    ("avatar_rohan.svg", "Rohan", "#D97706", "#FDE68A", "RO"),
]

out_dir = r"z:\7th Sem\Django\EDUREV project\static\images\avatars"

for filename, name, bg, accent, initials in avatars:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="80" height="80">
  <defs>
    <linearGradient id="grad_{initials}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg}"/>
      <stop offset="100%" stop-color="{bg}" stop-opacity="0.85"/>
    </linearGradient>
  </defs>
  <circle cx="40" cy="40" r="38" fill="url(#grad_{initials})" stroke="{accent}" stroke-width="2.5"/>
  <!-- Stylized avatar figure -->
  <circle cx="40" cy="31" r="14" fill="{accent}"/>
  <path d="M18,65 C20,50 30,46 40,46 C50,46 60,50 62,65 Z" fill="{accent}"/>
  <circle cx="40" cy="30" r="11" fill="{bg}"/>
  <text x="40" y="34" font-family="'Inter', sans-serif" font-size="10" font-weight="bold" fill="{accent}" text-anchor="middle" dominant-baseline="middle">{initials}</text>
</svg>"""
    with open(os.path.join(out_dir, filename), "w", encoding="utf-8") as f:
        f.write(svg)

print("Generated avatars successfully.")
