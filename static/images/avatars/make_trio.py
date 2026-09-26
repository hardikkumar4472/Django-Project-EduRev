import os

out_dir = r"z:\7th Sem\Django\EDUREV project\static\images\avatars"

# Female student 1 (long dark hair, smiling)
svg1 = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <defs>
    <radialGradient id="bg1" cx="50%" cy="40%" r="50%">
      <stop offset="0%" stop-color="#FED7AA"/>
      <stop offset="100%" stop-color="#F97316"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg1)"/>
  <!-- Hair back -->
  <path d="M26,38 C24,65 28,88 34,98 L66,98 C72,88 76,65 74,38 C72,20 28,20 26,38 Z" fill="#1C1917"/>
  <!-- Shoulders -->
  <path d="M22,100 C24,82 34,76 50,76 C66,76 76,82 78,100 Z" fill="#0F2942"/>
  <path d="M38,76 L50,88 L62,76 Z" fill="#FEEBC8"/>
  <!-- Neck & Face -->
  <rect x="44" y="62" width="12" height="16" fill="#FEEBC8"/>
  <ellipse cx="50" cy="50" rx="17" ry="21" fill="#FEEBC8"/>
  <!-- Hair front -->
  <path d="M33,35 C36,25 45,22 55,22 C65,22 68,28 67,35 C63,30 52,28 44,32 C38,35 34,42 33,48 Z" fill="#292524"/>
  <!-- Eyes & Smile -->
  <ellipse cx="43" cy="48" rx="2.5" ry="1.8" fill="#1C1917"/>
  <ellipse cx="57" cy="48" rx="2.5" ry="1.8" fill="#1C1917"/>
  <path d="M41,43 Q43,41 46,43" stroke="#292524" stroke-width="1.2" fill="none"/>
  <path d="M54,43 Q57,41 59,43" stroke="#292524" stroke-width="1.2" fill="none"/>
  <path d="M44,58 Q50,65 56,58" stroke="#BE185D" stroke-width="2.2" stroke-linecap="round" fill="#FFFFFF"/>
</svg>"""

# Male student 2 (glasses, dark hair, green shirt)
svg2 = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <defs>
    <radialGradient id="bg2" cx="50%" cy="40%" r="50%">
      <stop offset="0%" stop-color="#BAE6FD"/>
      <stop offset="100%" stop-color="#0284C7"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg2)"/>
  <!-- Shoulders -->
  <path d="M20,100 C22,78 35,74 50,74 C65,74 78,78 80,100 Z" fill="#0D9488"/>
  <rect x="44" y="60" width="12" height="16" fill="#FDE047" opacity="0.3"/>
  <rect x="43" y="60" width="14" height="16" fill="#FCD34D" opacity="0.4"/>
  <ellipse cx="50" cy="48" rx="18" ry="22" fill="#FDE68A"/>
  <!-- Hair -->
  <path d="M31,38 C31,24 40,18 50,18 C60,18 69,24 69,38 C65,26 55,24 44,25 C36,26 32,32 31,38 Z" fill="#1E293B"/>
  <!-- Glasses -->
  <rect x="36" y="44" width="11" height="9" rx="2.5" fill="none" stroke="#0F172A" stroke-width="2"/>
  <rect x="53" y="44" width="11" height="9" rx="2.5" fill="none" stroke="#0F172A" stroke-width="2"/>
  <line x1="47" y1="48" x2="53" y2="48" stroke="#0F172A" stroke-width="2"/>
  <circle cx="41.5" cy="48.5" r="2" fill="#0F172A"/>
  <circle cx="58.5" cy="48.5" r="2" fill="#0F172A"/>
  <!-- Smile -->
  <path d="M44,59 Q50,65 56,59" stroke="#9A3412" stroke-width="2.2" stroke-linecap="round" fill="none"/>
</svg>"""

# Female student 3 (wavy hair, smiling)
svg3 = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <defs>
    <radialGradient id="bg3" cx="50%" cy="40%" r="50%">
      <stop offset="0%" stop-color="#DDD6FE"/>
      <stop offset="100%" stop-color="#7C3AED"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg3)"/>
  <!-- Hair back -->
  <path d="M24,40 C22,70 26,92 32,98 L68,98 C74,92 78,70 76,40 C74,20 26,20 24,40 Z" fill="#451A03"/>
  <!-- Shoulders -->
  <path d="M20,100 C24,80 34,75 50,75 C66,75 76,80 80,100 Z" fill="#1E3A8A"/>
  <rect x="44" y="62" width="12" height="16" fill="#FED7AA"/>
  <ellipse cx="50" cy="49" rx="17" ry="21" fill="#FED7AA"/>
  <!-- Hair front waves -->
  <path d="M32,36 C36,24 45,21 54,21 C64,21 68,26 68,36 C64,30 52,27 43,30 C36,33 32,40 31,48 Z" fill="#78350F"/>
  <!-- Eyes & Smile -->
  <ellipse cx="43" cy="47" rx="2.5" ry="1.8" fill="#1C1917"/>
  <ellipse cx="57" cy="47" rx="2.5" ry="1.8" fill="#1C1917"/>
  <path d="M44,58 Q50,65 56,58" stroke="#BE185D" stroke-width="2.2" stroke-linecap="round" fill="#FFFFFF"/>
</svg>"""

with open(os.path.join(out_dir, "trio_1.svg"), "w", encoding="utf-8") as f:
    f.write(svg1)
with open(os.path.join(out_dir, "trio_2.svg"), "w", encoding="utf-8") as f:
    f.write(svg2)
with open(os.path.join(out_dir, "trio_3.svg"), "w", encoding="utf-8") as f:
    f.write(svg3)

print("Generated trio avatars successfully.")
