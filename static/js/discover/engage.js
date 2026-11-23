/* Star / save buttons on story cards (Home, Discover, Collections). */
(() => {
  const token = document.querySelector('meta[name="csrf-token"]').content;
  document.addEventListener('click', async e => {
    const btn = e.target.closest('[data-toggle]');
    if (!btn) return;
    e.preventDefault();
    const card = btn.closest('[data-id]');
    btn.disabled = true;
    try {
      const res = await fetch(`/discover/toggle/${btn.dataset.toggle}/${card.dataset.id}/`, { method: 'POST', headers: { 'X-CSRFToken': token } });
      if (!res.ok) throw new Error();
      const d = await res.json();
      btn.setAttribute('aria-pressed', d.on);
      if (btn.dataset.toggle === 'star') {
        btn.querySelector('.ico').textContent = d.on ? '★' : '☆';
        btn.querySelector('.count').textContent = d.stars;
      } else {
        btn.querySelector('.lbl').textContent = d.on ? 'Saved ✓' : 'Save';
      }
      if (!d.on && card.dataset.removeOn === btn.dataset.toggle) {
        card.classList.add('is-leaving');
        setTimeout(() => card.remove(), 350);
      }
    } catch (err) {
      btn.title = 'Could not update. Try again.';
    } finally { btn.disabled = false; }
  });
})();
