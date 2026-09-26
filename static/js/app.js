// CampusExchange Client Interactions — P04 Master Spec

document.addEventListener('DOMContentLoaded', function() {
  // 1. Live Proposal Expiration Countdown Timer
  const countdownElements = document.querySelectorAll('[data-countdown]');
  countdownElements.forEach(el => {
    const targetIso = el.getAttribute('data-countdown');
    if (!targetIso) return;
    const targetDate = new Date(targetIso).getTime();

    function updateCountdown() {
      const now = new Date().getTime();
      const distance = targetDate - now;

      if (distance < 0) {
        el.textContent = "EXPIRED";
        el.classList.add('badge-red');
        return;
      }

      const hours = Math.floor(distance / (1000 * 60 * 60));
      const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((distance % (1000 * 60)) / 1000);

      el.textContent = `${hours}h ${minutes}m ${seconds}s remaining`;
    }

    updateCountdown();
    setInterval(updateCountdown, 1000);
  });

  // 2. Interactive Bed Selection / Tooltip
  const bedUnits = document.querySelectorAll('.bed-unit');
  const detailsPanel = document.getElementById('bed-details-panel');

  bedUnits.forEach(unit => {
    unit.addEventListener('click', function() {
      const bedNumber = this.getAttribute('data-bed-number');
      const occupant = this.getAttribute('data-occupant');
      const status = this.getAttribute('data-status');
      
      if (detailsPanel) {
        detailsPanel.innerHTML = `
          <div class="card" style="margin-top: 1rem; border-left: 4px solid var(--color-teal);">
            <h4 style="font-weight: 700; color: var(--color-navy);">${bedNumber} Information</h4>
            <p style="font-size: 0.9rem; margin-top: 0.25rem;"><strong>Occupancy Status:</strong> ${status}</p>
            <p style="font-size: 0.9rem;"><strong>Current Resident:</strong> ${occupant || 'None (Vacant)'}</p>
          </div>
        `;
      }
    });
  });
});
