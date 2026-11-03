import sys

with open('templates/landing.html', 'r', encoding='utf-8') as f:
    content = f.read()

target = """          <a href="{% url 'login' %}" class="btn btn-outline" style="border-color: #FED7AA; color: #EA580C; padding: 0.75rem 1.4rem; font-weight: 700; background: #FFFFFF;">
            Sign In with ID
          </a>
        </div>
      </div>

    </div>
  </section>

  <!-- ========================================================================
       COMPREHENSIVE FAQS SECTION (INTERACTIVE ACCORDION)"""

testimonials_html = """          <a href="{% url 'login' %}" class="btn btn-outline" style="border-color: #FED7AA; color: #EA580C; padding: 0.75rem 1.4rem; font-weight: 700; background: #FFFFFF;">
            Sign In with ID
          </a>
        </div>
      </div>

    </div>
  </section>

  <!-- ========================================================================
       WHAT STUDENTS SAY SECTION (3D CIRCULAR TESTIMONIAL CAROUSEL)
       ======================================================================== -->
  <section id="what-students-say" class="lpu-testimonials-section">
    <!-- Subtle circular background orbit decoration -->
    <div class="circular-orbit-decor" aria-hidden="true">
      <div class="orbit-ring orbit-ring-outer"></div>
      <div class="orbit-ring orbit-ring-inner"></div>
    </div>

    <div class="testimonials-header-wrap">
      <span class="section-badge-pill">💬 Real Hosteller Experiences</span>
      <h2 class="testimonials-main-title">What Students Say About EDUREV</h2>
      <p class="testimonials-subtitle">
        Over 2,400+ students across BH-1 to BH-10 and GH-1 to GH-10 have exchanged their rooms seamlessly with zero paperwork and instant digital approvals.
      </p>

      <div class="testimonials-stat-badges">
        <span class="testi-stat-chip">⭐ <strong>4.9 / 5</strong> Overall Rating</span>
        <span class="testi-stat-chip">🔄 <strong>2,400+</strong> Swaps Completed</span>
        <span class="testi-stat-chip">⚡ <strong>99.4%</strong> Warden Approval Rate</span>
      </div>
    </div>

    <!-- Circular 3D Carousel Stage -->
    <div class="circular-stage-wrapper" id="circularTestimonialsCarousel">
      
      <!-- Nav Button: Previous -->
      <button class="circular-nav-btn prev-btn" id="circTestiPrev" aria-label="Previous Student Review">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
      </button>

      <!-- Carousel Cards Track -->
      <div class="circular-cards-track" id="circTestiTrack">
        
        <!-- CARD 1: Aarav Sharma -->
        <div class="circular-card" data-index="0">
          <div class="card-quote-mark">“</div>
          <div class="card-student-header">
            <div class="student-avatar-circle" style="background: linear-gradient(135deg, #F37021, #EA580C);">
              <span>AS</span>
              <span class="verified-dot-badge" title="Verified LPU Student">✓</span>
            </div>
            <div class="student-info-meta">
              <h4 class="student-name">Aarav Sharma</h4>
              <span class="student-branch">B.Tech CSE &bull; 3rd Year</span>
            </div>
            <div class="student-stars">★★★★★</div>
          </div>

          <div class="route-exchange-pill">
            <span class="route-tag-icon">🏠</span>
            <span class="route-path">BH-4 <span class="route-arrow">➔</span> BH-7</span>
            <span class="route-type-badge">4-Seater AC</span>
          </div>

          <p class="student-quote-body">
            "Was struggling to find night-study peace in my old wing. Connected with a fellow coder from BH-7 through EDUREV, did the lifestyle quiz, and matched in 10 minutes. Warden approved it digitally the next morning!"
          </p>

          <div class="card-footer-stamp">
            <span class="stamp-check">✓</span>
            <span>Direct 2-Party Swap &bull; Warden Verified</span>
          </div>
        </div>

        <!-- CARD 2: Ananya Verma -->
        <div class="circular-card" data-index="1">
          <div class="card-quote-mark">“</div>
          <div class="card-student-header">
            <div class="student-avatar-circle" style="background: linear-gradient(135deg, #EC4899, #8B5CF6);">
              <span>AV</span>
              <span class="verified-dot-badge" title="Verified LPU Student">✓</span>
            </div>
            <div class="student-info-meta">
              <h4 class="student-name">Ananya Verma</h4>
              <span class="student-branch">B.Des Fashion &bull; 2nd Year</span>
            </div>
            <div class="student-stars">★★★★★</div>
          </div>

          <div class="route-exchange-pill">
            <span class="route-tag-icon">🏠</span>
            <span class="route-path">GH-2 <span class="route-arrow">➔</span> GH-5</span>
            <span class="route-type-badge">3-Seater</span>
          </div>

          <p class="student-quote-body">
            "Moving closer to the design studio block saved me 25 minutes of walking every single morning. The multi-hop swap chain feature is unbelievable—3 students swapped simultaneously without any confusion."
          </p>

          <div class="card-footer-stamp">
            <span class="stamp-check">✓</span>
            <span>Multi-Hop Cycle &bull; 98% Compatibility</span>
          </div>
        </div>

        <!-- CARD 3: Rohan Patel -->
        <div class="circular-card" data-index="2">
          <div class="card-quote-mark">“</div>
          <div class="card-student-header">
            <div class="student-avatar-circle" style="background: linear-gradient(135deg, #0284C7, #0F766E);">
              <span>RP</span>
              <span class="verified-dot-badge" title="Verified LPU Student">✓</span>
            </div>
            <div class="student-info-meta">
              <h4 class="student-name">Rohan Patel</h4>
              <span class="student-branch">MBA &bull; Final Year</span>
            </div>
            <div class="student-stars">★★★★★</div>
          </div>

          <div class="route-exchange-pill">
            <span class="route-tag-icon">🏠</span>
            <span class="route-path">BH-1 <span class="route-arrow">➔</span> BH-8</span>
            <span class="route-type-badge">2-Seater AC</span>
          </div>

          <p class="student-quote-body">
            "Zero paperwork hassle. We didn't have to stand in long warden office lines or wait days for physical signature stamps. The automated digital clearance letter was accepted at the caretaker desk in 2 minutes flat."
          </p>

          <div class="card-footer-stamp">
            <span class="stamp-check">✓</span>
            <span>Digital Clearance Letter &bull; 100% Hassle-Free</span>
          </div>
        </div>

        <!-- CARD 4: Priya Sundaram -->
        <div class="circular-card" data-index="3">
          <div class="card-quote-mark">“</div>
          <div class="card-student-header">
            <div class="student-avatar-circle" style="background: linear-gradient(135deg, #10B981, #059669);">
              <span>PS</span>
              <span class="verified-dot-badge" title="Verified LPU Student">✓</span>
            </div>
            <div class="student-info-meta">
              <h4 class="student-name">Priya Sundaram</h4>
              <span class="student-branch">B.Tech ECE &bull; 2nd Year</span>
            </div>
            <div class="student-stars">★★★★★</div>
          </div>

          <div class="route-exchange-pill">
            <span class="route-tag-icon">🏠</span>
            <span class="route-path">GH-3 <span class="route-arrow">➔</span> GH-1</span>
            <span class="route-type-badge">1-Seater Standard</span>
          </div>

          <p class="student-quote-body">
            "Wanted a quiet single-seater room for GATE exam prep. Found a graduating senior completing tenure early. The platform handled the administrative rules, gender segregation, and cycle validation smoothly."
          </p>

          <div class="card-footer-stamp">
            <span class="stamp-check">✓</span>
            <span>Quiet Study Wing &bull; Caretaker Approved</span>
          </div>
        </div>

        <!-- CARD 5: Vikramaditya Malhotra -->
        <div class="circular-card" data-index="4">
          <div class="card-quote-mark">“</div>
          <div class="card-student-header">
            <div class="student-avatar-circle" style="background: linear-gradient(135deg, #F59E0B, #D97706);">
              <span>VM</span>
              <span class="verified-dot-badge" title="Verified LPU Student">✓</span>
            </div>
            <div class="student-info-meta">
              <h4 class="student-name">Vikramaditya Malhotra</h4>
              <span class="student-branch">BBA LLB &bull; 4th Year</span>
            </div>
            <div class="student-stars">★★★★★</div>
          </div>

          <div class="route-exchange-pill">
            <span class="route-tag-icon">🏠</span>
            <span class="route-path">BH-5 <span class="route-arrow">➔</span> BH-2</span>
            <span class="route-type-badge">3-Seater Cooler</span>
          </div>

          <p class="student-quote-body">
            "Our whole basketball squad wanted to be together in BH-2 right beside the sports complex. Swapped my room in 3 days. Clean, transparent, authenticated, and completely approved by the Chief Warden."
          </p>

          <div class="card-footer-stamp">
            <span class="stamp-check">✓</span>
            <span>Sports Wing Transfer &bull; Verified Hosteller</span>
          </div>
        </div>

        <!-- CARD 6: Ishita Gupta -->
        <div class="circular-card" data-index="5">
          <div class="card-quote-mark">“</div>
          <div class="card-student-header">
            <div class="student-avatar-circle" style="background: linear-gradient(135deg, #8B5CF6, #6366F1);">
              <span>IG</span>
              <span class="verified-dot-badge" title="Verified LPU Student">✓</span>
            </div>
            <div class="student-info-meta">
              <h4 class="student-name">Ishita Gupta</h4>
              <span class="student-branch">B.Sc Biotech &bull; 3rd Year</span>
            </div>
            <div class="student-stars">★★★★★</div>
          </div>

          <div class="route-exchange-pill">
            <span class="route-tag-icon">🏠</span>
            <span class="route-path">GH-6 <span class="route-arrow">➔</span> GH-4</span>
            <span class="route-type-badge">4-Seater AC</span>
          </div>

          <p class="student-quote-body">
            "The lifestyle quiz filter was an absolute lifesaver. I wanted non-smoking, early-riser roommates who keep study hours tidy. EDUREV matched me with like-minded girls in GH-4 within 2 days!"
          </p>

          <div class="card-footer-stamp">
            <span class="stamp-check">✓</span>
            <span>Lifestyle Matched &bull; Perfect Roommates</span>
          </div>
        </div>

        <!-- CARD 7: Siddharth Nair -->
        <div class="circular-card" data-index="6">
          <div class="card-quote-mark">“</div>
          <div class="card-student-header">
            <div class="student-avatar-circle" style="background: linear-gradient(135deg, #0EA5E9, #2563EB);">
              <span>SN</span>
              <span class="verified-dot-badge" title="Verified LPU Student">✓</span>
            </div>
            <div class="student-info-meta">
              <h4 class="student-name">Siddharth Nair</h4>
              <span class="student-branch">B.Tech Mechanical &bull; 3rd Year</span>
            </div>
            <div class="student-stars">★★★★★</div>
          </div>

          <div class="route-exchange-pill">
            <span class="route-tag-icon">🏠</span>
            <span class="route-path">BH-3 <span class="route-arrow">➔</span> BH-6</span>
            <span class="route-type-badge">2-Seater Standard</span>
          </div>

          <p class="student-quote-body">
            "The real-time notifications popped up the minute a room in BH-6 opened up. We reviewed each other's profiles, agreed on the swap, and keys were handed over by Saturday morning without a hitch!"
          </p>

          <div class="card-footer-stamp">
            <span class="stamp-check">✓</span>
            <span>Real-time Notification Match &bull; Key Handover Done</span>
          </div>
        </div>

        <!-- CARD 8: Sneha Kulkarni -->
        <div class="circular-card" data-index="7">
          <div class="card-quote-mark">“</div>
          <div class="card-student-header">
            <div class="student-avatar-circle" style="background: linear-gradient(135deg, #EC4899, #F43F5E);">
              <span>SK</span>
              <span class="verified-dot-badge" title="Verified LPU Student">✓</span>
            </div>
            <div class="student-info-meta">
              <h4 class="student-name">Sneha Kulkarni</h4>
              <span class="student-branch">B.Pharm &bull; 2nd Year</span>
            </div>
            <div class="student-stars">★★★★★</div>
          </div>

          <div class="route-exchange-pill">
            <span class="route-tag-icon">🏠</span>
            <span class="route-path">GH-1 <span class="route-arrow">➔</span> GH-3</span>
            <span class="route-type-badge">2-Seater AC</span>
          </div>

          <p class="student-quote-body">
            "Hostel room changes used to take weeks of chasing signatures across blocks. With EDUREV, caretaker biometric verification and instant digital transfer letters made the entire transition effortless."
          </p>

          <div class="card-footer-stamp">
            <span class="stamp-check">✓</span>
            <span>Digital Biometric Clearance &bull; Verified Hosteller</span>
          </div>
        </div>

      </div>

      <!-- Nav Button: Next -->
      <button class="circular-nav-btn next-btn" id="circTestiNext" aria-label="Next Student Review">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </button>

    </div>

    <!-- Circular Navigation Indicators & Play/Pause -->
    <div class="circular-controls-bar">
      <div class="circular-dots-wrap" id="circTestiDots"></div>
      <div class="circular-play-pause-wrap">
        <button class="circular-play-toggle" id="circPlayToggle" title="Pause or Resume Auto-Rotation">
          <span id="circPlayIcon">⏸</span>
        </button>
      </div>
    </div>

  </section>

  <!-- ========================================================================
       COMPREHENSIVE FAQS SECTION (INTERACTIVE ACCORDION)"""

if target in content:
    content = content.replace(target, testimonials_html)
    with open('templates/landing.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Injected testimonials markup into landing.html')
else:
    print('ERROR: Target string not found')
    sys.exit(1)

