/* ============================================================
   Holiday Planner – app.js
   ============================================================ */

const API_BASE = 'http://localhost:8000';

// ── State ──────────────────────────────────────────────────
let currentItinerary = null;
let currentTripRequest = null;

// ── DOM refs ────────────────────────────────────────────────
const form              = document.getElementById('planner-form');
const btnGenerate       = document.getElementById('btn-generate');
const btnSave           = document.getElementById('btn-save');
const btnNew            = document.getElementById('btn-new');
const btnViewSaved      = document.getElementById('btn-view-saved');
const btnBackFromSaved  = document.getElementById('btn-back-from-saved');

const plannerSection    = document.getElementById('planner-section');
const resultsSection    = document.getElementById('results-section');
const resultsContainer  = document.getElementById('results-container');
const savedSection      = document.getElementById('saved-section');
const savedList         = document.getElementById('saved-list');
const toast             = document.getElementById('toast');

// ── Chips ───────────────────────────────────────────────────
function initChips() {
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => chip.classList.toggle('active'));
  });
}

function getChipValues(containerId) {
  return [...document.querySelectorAll(`#${containerId} .chip.active`)]
    .map(c => c.dataset.value);
}

// ── Provider cards ──────────────────────────────────────────
function initProviderCards() {
  document.querySelectorAll('.provider-card').forEach(card => {
    const radio = card.querySelector('input[type="radio"]');
    radio.addEventListener('change', () => {
      document.querySelectorAll('.provider-card').forEach(c => c.classList.remove('selected'));
      if (radio.checked) card.classList.add('selected');
    });
    card.addEventListener('click', () => {
      radio.checked = true;
      radio.dispatchEvent(new Event('change'));
    });
  });
}

// ── Children toggle ─────────────────────────────────────────
function initChildrenToggle() {
  const checkbox = document.getElementById('has_children');
  const group    = document.getElementById('children-ages-group');
  checkbox.addEventListener('change', () => {
    group.style.display = checkbox.checked ? 'flex' : 'none';
  });
}

// ── Day accordion ────────────────────────────────────────────
function initDayAccordion() {
  document.querySelectorAll('.day-header').forEach(header => {
    header.addEventListener('click', () => {
      const card = header.closest('.day-card');
      card.classList.toggle('open');
    });
  });
}

// ── Toast ────────────────────────────────────────────────────
let toastTimeout;
function showToast(msg, type = '') {
  clearTimeout(toastTimeout);
  toast.textContent = msg;
  toast.className = `toast ${type ? 'toast-' + type : ''}`;
  toast.classList.remove('hidden');
  toastTimeout = setTimeout(() => toast.classList.add('hidden'), 4000);
}

// ── Loading state ─────────────────────────────────────────────
function setLoading(isLoading) {
  const text    = btnGenerate.querySelector('.btn-text');
  const spinner = btnGenerate.querySelector('.btn-spinner');
  btnGenerate.disabled = isLoading;
  if (isLoading) {
    text.textContent = 'Generating…';
    spinner.classList.remove('hidden');
  } else {
    text.textContent = '✨ Generate My Itinerary';
    spinner.classList.add('hidden');
  }
}

// ── Form data collection ──────────────────────────────────────
function collectFormData() {
  const f = form;
  const destinationsRaw = f.destinations.value.trim();
  const destinations = destinationsRaw.split(',').map(d => d.trim()).filter(Boolean);

  const childrenAgesRaw = document.getElementById('children_ages').value.trim();
  const children_ages = childrenAgesRaw
    ? childrenAgesRaw.split(',').map(a => parseInt(a.trim(), 10)).filter(n => !isNaN(n))
    : [];

  const ai_provider = document.querySelector('input[name="ai_provider"]:checked')?.value || 'gemini';

  return {
    origin_city:              f.origin_city.value.trim(),
    destinations,
    departure_date:           f.departure_date.value,
    return_date:              f.return_date.value,
    travellers:               parseInt(f.travellers.value, 10) || 1,
    cabin_class:              f.cabin_class.value,
    skip_flights:             f.skip_flights.checked,
    trip_purpose:             f.trip_purpose.value,
    travel_style:             f.travel_style.value,
    accommodation_preference: f.accommodation_preference.value,
    skip_hotels:              f.skip_hotels.checked,
    pace:                     f.pace.value,
    has_children:             f.has_children.checked,
    children_ages,
    has_elderly:              f.has_elderly.checked,
    mobility_requirements:    f.mobility_requirements.checked,
    interests:                getChipValues('interests-chips'),
    dietary_requirements:     getChipValues('dietary-chips'),
    special_instructions:     f.special_instructions.value.trim() || null,
    ai_provider,
  };
}

// ── Form validation ───────────────────────────────────────────
function validateForm(data) {
  if (!data.origin_city)        return 'Please enter your departure city.';
  if (!data.destinations.length) return 'Please enter at least one destination.';
  if (!data.departure_date)     return 'Please select a departure date.';
  if (!data.return_date)        return 'Please select a return date.';
  if (data.departure_date >= data.return_date) return 'Return date must be after departure date.';
  return null;
}

// ── Render helpers ────────────────────────────────────────────
function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function renderTimeSlot(label, slot) {
  if (!slot) return '';
  return `
    <div class="time-slot">
      <div class="time-slot-label">${esc(label)}</div>
      <h4>${esc(slot.activity)}</h4>
      <p>${esc(slot.description)}</p>
      ${slot.tip  ? `<p class="tip">💡 ${esc(slot.tip)}</p>` : ''}
      ${slot.cost ? `<p class="cost">${esc(slot.cost)}</p>` : ''}
    </div>`;
}

function renderDay(day) {
  const meals = day.meals || {};
  const acc   = day.accommodation || {};
  return `
    <div class="day-card" data-day="${day.day}">
      <div class="day-header">
        <span class="day-number">Day ${esc(day.day)} · ${esc(day.date)}</span>
        <span class="day-title">${esc(day.title)}</span>
        <span class="day-location">📍 ${esc(day.location)}</span>
        <span class="day-chevron">▼</span>
      </div>
      <div class="day-body">
        <div class="time-slots">
          ${renderTimeSlot('Morning', day.morning)}
          ${renderTimeSlot('Afternoon', day.afternoon)}
          ${renderTimeSlot('Evening', day.evening)}
        </div>
        <div class="day-extras">
          ${meals.breakfast || meals.lunch || meals.dinner ? `
            <div class="extra-block">
              <strong>🍽 Meals</strong>
              ${meals.breakfast ? `<p>☀ ${esc(meals.breakfast)}</p>` : ''}
              ${meals.lunch     ? `<p>🌤 ${esc(meals.lunch)}</p>` : ''}
              ${meals.dinner    ? `<p>🌙 ${esc(meals.dinner)}</p>` : ''}
            </div>` : ''}
          ${acc.name ? `
            <div class="extra-block">
              <strong>🏨 Stay</strong>
              <p>${esc(acc.name)}${acc.area ? `, ${esc(acc.area)}` : ''}</p>
            </div>` : ''}
          ${day.transport ? `
            <div class="extra-block">
              <strong>🚇 Transport</strong>
              <p>${esc(day.transport)}</p>
            </div>` : ''}
          ${day.day_budget ? `
            <div class="extra-block">
              <strong>💰 Day Budget</strong>
              <p>${esc(day.day_budget)}</p>
            </div>` : ''}
        </div>
      </div>
    </div>`;
}

function renderBudget(cost) {
  if (!cost) return '';
  const rows = [
    ['Accommodation',  cost.accommodation],
    ['Food',           cost.food],
    ['Activities',     cost.activities],
    ['Local Transport',cost.local_transport],
    ['Total / Person', cost.total_per_person],
  ].filter(([, v]) => v);
  if (!rows.length) return '';
  return `
    <div class="budget-card">
      <h3>💰 Estimated Trip Cost</h3>
      <div class="budget-grid">
        ${rows.map(([k, v]) => `
          <div class="budget-item">
            <strong>${esc(k)}</strong>
            <span>${esc(v)}</span>
          </div>`).join('')}
      </div>
    </div>`;
}

function renderPractical(info) {
  if (!info) return '';
  const packing = info.packing || info.packing_suggestions || [];
  return `
    <div class="practical-card">
      <h3>📋 Practical Info</h3>
      <div class="practical-grid">
        ${info.currency      ? `<div class="practical-item"><strong>Currency</strong>${esc(info.currency)}</div>` : ''}
        ${info.language      ? `<div class="practical-item"><strong>Language</strong>${esc(info.language)}</div>` : ''}
        ${info.transport_tip ? `<div class="practical-item"><strong>Transport</strong>${esc(info.transport_tip)}</div>` : ''}
        ${info.safety_tip    ? `<div class="practical-item"><strong>Safety</strong>${esc(info.safety_tip)}</div>` : ''}
      </div>
      ${packing.length ? `
        <div style="margin-top:.75rem">
          <strong style="font-size:.75rem;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);">🎒 Pack</strong>
          <div class="packing-list">
            ${packing.map(p => `<span class="packing-tag">${esc(p)}</span>`).join('')}
          </div>
        </div>` : ''}
    </div>`;
}

function renderFlights(flights) {
  if (!flights || !flights.available) return '';
  const { skyscanner, google_flights, origin, destination, departure, adults, cabin_class } = flights;
  return `
    <div class="live-section">
      <h3>✈ Search Flights</h3>
      <p style="font-size:.85rem;color:var(--muted);margin-bottom:1rem">
        ${esc(origin)} → ${esc(destination)} · ${esc(departure)}
        ${flights.return ? ` → ${esc(flights.return)}` : ''} · ${esc(adults)} traveller${adults > 1 ? 's' : ''} · ${esc(cabin_class)}
      </p>
      <div style="display:flex;gap:.75rem;flex-wrap:wrap">
        <a href="${skyscanner}" target="_blank" rel="noopener" class="btn btn-primary">
          Search on Skyscanner →
        </a>
        <a href="${google_flights}" target="_blank" rel="noopener" class="btn btn-secondary">
          Search on Google Flights →
        </a>
      </div>
      <p style="font-size:.75rem;color:var(--muted);margin-top:.6rem">
        Links open with your dates, route and passenger count pre-filled.
      </p>
    </div>`;
}

function renderHotels(hotels) {
  if (!hotels || !hotels.available || !hotels.hotels?.length) return '';
  return `
    <div class="live-section">
      <h3>🏨 Live Hotel Options</h3>
      <p style="font-size:.8rem;color:var(--muted);margin-bottom:.75rem">Prices from Booking.com. Click to book.</p>
      ${hotels.hotels.map(h => {
        const bookUrl = h.url || `https://www.booking.com/search.html?ss=${encodeURIComponent(h.name + ' ' + (h.city || ''))}`;
        return `
        <div class="offer-card">
          <div style="flex:1">
            <div style="font-weight:700">${esc(h.name)}</div>
            <div class="offer-segments">
              ${h.rating       ? `⭐ ${esc(h.rating)} stars · ` : ''}
              ${h.review_score ? `${esc(h.review_score)}/10 ${esc(h.review_word)} · ` : ''}
              ${esc(h.address || h.city || '')}
            </div>
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:.4rem">
            ${h.price_per_night ? `<div class="offer-price">£${esc(h.price_per_night)} <small>/ stay</small></div>` : ''}
            <a href="${bookUrl}" target="_blank" rel="noopener" class="btn btn-primary" style="white-space:nowrap">Book →</a>
          </div>
        </div>`;
      }).join('')}
    </div>`;
}

function renderResults(itinerary, flights, hotels) {
  const highlights = itinerary.highlights || [];
  return `
    <div class="results-header">
      <h2>Your Itinerary 🗺</h2>
      <p class="results-summary">${esc(itinerary.summary)}</p>
      ${highlights.length ? `
        <div class="highlights-list">
          ${highlights.map(h => `<span class="highlight-tag">${esc(h)}</span>`).join('')}
        </div>` : ''}
    </div>
    ${renderFlights(flights)}
    ${renderHotels(hotels)}
    ${(itinerary.days || []).map(renderDay).join('')}
    ${renderBudget(itinerary.estimated_cost || itinerary.estimated_total_cost)}
    ${renderPractical(itinerary.practical_info)}`;
}

// ── Show/hide sections ────────────────────────────────────────
function showPlanner() {
  plannerSection.classList.remove('hidden');
  resultsSection.classList.add('hidden');
  savedSection.classList.add('hidden');
}
function showResults() {
  plannerSection.classList.add('hidden');
  resultsSection.classList.remove('hidden');
  savedSection.classList.add('hidden');
  resultsSection.scrollIntoView({ behavior: 'smooth' });
}
function showSaved() {
  plannerSection.classList.add('hidden');
  resultsSection.classList.add('hidden');
  savedSection.classList.remove('hidden');
}

// ── Generate itinerary ────────────────────────────────────────
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = collectFormData();
  const err  = validateForm(data);
  if (err) { showToast(err, 'error'); return; }

  setLoading(true);
  resultsContainer.innerHTML = `
    <div class="loading-overlay">
      <div class="loading-spinner"></div>
      <p id="loading-msg">Starting your trip planning…</p>
    </div>`;
  showResults();

  const loadingMessages = [
    '✈️ Searching for the best flight routes…',
    '🏨 Scouting top-rated hotels for your dates…',
    '🗺️ Building your personalised day-by-day itinerary…',
    '🍽️ Finding the best local restaurants…',
    '🎯 Matching activities to your interests…',
    '🌤️ Checking the best times to visit each spot…',
    '💰 Calculating your budget breakdown…',
    '🎒 Preparing your packing suggestions…',
    '📋 Finalising practical travel tips…',
    '✨ Almost there — polishing your itinerary…',
  ];
  let msgIndex = 0;
  const msgEl = document.getElementById('loading-msg');
  const msgInterval = setInterval(() => {
    msgIndex = (msgIndex + 1) % loadingMessages.length;
    if (msgEl) msgEl.textContent = loadingMessages[msgIndex];
  }, 3000);

  try {
    // Generate itinerary
    const iRes = await fetch(`${API_BASE}/api/itinerary/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!iRes.ok) {
      const errBody = await iRes.json().catch(() => ({}));
      throw new Error(errBody.detail || `API error ${iRes.status}`);
    }
    const iData = await iRes.json();
    currentItinerary  = iData.itinerary;
    currentTripRequest = data;

    // Search flights & hotels in parallel (best effort, skippable)
    let flightsData = null;
    let hotelsData  = null;

    const destination = data.destinations[0];
    const searches    = [];

    if (!data.skip_flights) {
      searches.push(
        fetch(`${API_BASE}/api/flights/search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            origin_city:      data.origin_city,
            destination_city: destination,
            departure_date:   data.departure_date,
            return_date:      data.return_date,
            adults:           data.travellers,
            cabin_class:      data.cabin_class,
          }),
        }).then(r => r.json()).catch(() => null)
      );
    } else {
      searches.push(Promise.resolve(null));
    }

    if (!data.skip_hotels) {
      searches.push(
        fetch(`${API_BASE}/api/hotels/search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            city:      destination,
            check_in:  data.departure_date,
            check_out: data.return_date,
            adults:    data.travellers,
            rooms:     1,
          }),
        }).then(r => r.json()).catch(() => null)
      );
    } else {
      searches.push(Promise.resolve(null));
    }

    const [fResult, hResult] = await Promise.all(searches);
    flightsData = fResult;
    hotelsData  = hResult;

    resultsContainer.innerHTML = renderResults(currentItinerary, flightsData, hotelsData);
    initDayAccordion();
    // Auto-open first day
    const firstDay = resultsContainer.querySelector('.day-card');
    if (firstDay) firstDay.classList.add('open');

    showToast('Itinerary ready! 🎉', 'success');
  } catch (err) {
    resultsContainer.innerHTML = `
      <div class="loading-overlay">
        <p style="color:var(--error)">⚠ ${esc(err.message)}</p>
        <button class="btn btn-ghost mt-md" id="btn-retry">Try Again</button>
      </div>`;
    document.getElementById('btn-retry')?.addEventListener('click', showPlanner);
    showToast(err.message, 'error');
  } finally {
    clearInterval(msgInterval);
    setLoading(false);
  }
});

// ── Save itinerary ────────────────────────────────────────────
btnSave.addEventListener('click', async () => {
  if (!currentItinerary || !currentTripRequest) return;
  try {
    const res = await fetch(`${API_BASE}/api/itinerary/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trip_request: currentTripRequest, itinerary: currentItinerary }),
    });
    const data = await res.json();
    if (data.success) {
      showToast('Trip saved! 💾', 'success');
    } else {
      showToast('Save failed. Is Supabase configured?', 'error');
    }
  } catch {
    showToast('Save failed. Is Supabase configured?', 'error');
  }
});

// ── New trip ──────────────────────────────────────────────────
btnNew.addEventListener('click', () => {
  showPlanner();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// ── View saved ────────────────────────────────────────────────
btnViewSaved.addEventListener('click', async () => {
  showSaved();
  savedList.innerHTML = '<p style="color:var(--muted)">Loading…</p>';
  try {
    const res  = await fetch(`${API_BASE}/api/itinerary/`);
    const data = await res.json();
    if (!data.length) {
      savedList.innerHTML = '<p style="color:var(--muted)">No saved trips yet.</p>';
      return;
    }
    savedList.innerHTML = data.map(item => {
      const req = item.trip_request || {};
      const dests = (req.destinations || []).join(', ') || '—';
      const date  = item.created_at ? new Date(item.created_at).toLocaleDateString() : '';
      return `
        <div class="saved-item">
          <div class="saved-item-info">
            <strong>${esc(req.origin_city || '—')} → ${esc(dests)}</strong>
            <div class="saved-item-date">${esc(req.departure_date || '')} – ${esc(req.return_date || '')} · Saved ${esc(date)}</div>
          </div>
          <button class="btn btn-secondary" data-id="${esc(item.id)}">View</button>
        </div>`;
    }).join('');

    savedList.querySelectorAll('[data-id]').forEach(btn => {
      btn.addEventListener('click', () => loadSaved(btn.dataset.id));
    });
  } catch {
    savedList.innerHTML = '<p style="color:var(--error)">Could not load saved trips.</p>';
  }
});

async function loadSaved(id) {
  showResults();
  resultsContainer.innerHTML = `<div class="loading-overlay"><div class="loading-spinner"></div><p>Loading…</p></div>`;
  try {
    const res  = await fetch(`${API_BASE}/api/itinerary/${id}`);
    if (!res.ok) throw new Error('Not found');
    const data = await res.json();
    currentItinerary   = data.itinerary;
    currentTripRequest = data.trip_request;
    resultsContainer.innerHTML = renderResults(currentItinerary, data.flights, data.hotels);
    initDayAccordion();
    const firstDay = resultsContainer.querySelector('.day-card');
    if (firstDay) firstDay.classList.add('open');
  } catch {
    showToast('Could not load saved trip.', 'error');
    showSaved();
  }
}

btnBackFromSaved.addEventListener('click', showPlanner);

// ── Persist form to localStorage ────────────────────────────────
const STORAGE_KEY = 'holiday_planner_form';

function saveFormState() {
  const state = {
    // Text / number / date inputs
    origin_city:              document.getElementById('origin_city').value,
    destinations:             document.getElementById('destinations').value,
    departure_date:           document.getElementById('departure_date').value,
    return_date:              document.getElementById('return_date').value,
    travellers:               document.getElementById('travellers').value,
    cabin_class:              document.getElementById('cabin_class').value,
    trip_purpose:             document.getElementById('trip_purpose').value,
    travel_style:             document.getElementById('travel_style').value,
    accommodation_preference: document.getElementById('accommodation_preference').value,
    pace:                     document.getElementById('pace').value,
    special_instructions:     document.getElementById('special_instructions').value,
    // Checkboxes
    has_children:             document.getElementById('has_children').checked,
    children_ages:            document.getElementById('children_ages').value,
    has_elderly:              document.getElementById('has_elderly').checked,
    mobility_requirements:    document.getElementById('mobility_requirements').checked,
    skip_flights:             document.getElementById('skip_flights').checked,
    skip_hotels:              document.getElementById('skip_hotels').checked,
    // Chips
    interests:                getChipValues('interests-chips'),
    dietary:                  getChipValues('dietary-chips'),
    // AI provider
    ai_provider:              document.querySelector('input[name="ai_provider"]:checked')?.value || 'gemini',
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function restoreFormState() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return;
  try {
    const s = JSON.parse(raw);

    // Text / number / date
    const fields = ['origin_city','destinations','departure_date','return_date',
                    'travellers','cabin_class','trip_purpose','travel_style',
                    'accommodation_preference','pace','special_instructions','children_ages'];
    fields.forEach(id => {
      const el = document.getElementById(id);
      if (el && s[id] != null) el.value = s[id];
    });

    // Checkboxes
    ['has_children','has_elderly','mobility_requirements','skip_flights','skip_hotels'].forEach(id => {
      const el = document.getElementById(id);
      if (el && s[id] != null) el.checked = s[id];
    });
    // Trigger children toggle so age field shows/hides correctly
    document.getElementById('has_children').dispatchEvent(new Event('change'));

    // Chips — interests
    document.querySelectorAll('#interests-chips .chip').forEach(chip => {
      chip.classList.toggle('active', (s.interests || []).includes(chip.dataset.value));
    });
    // Chips — dietary
    document.querySelectorAll('#dietary-chips .chip').forEach(chip => {
      chip.classList.toggle('active', (s.dietary || []).includes(chip.dataset.value));
    });

    // AI provider
    if (s.ai_provider) {
      const radio = document.querySelector(`input[name="ai_provider"][value="${s.ai_provider}"]`);
      if (radio) { radio.checked = true; radio.dispatchEvent(new Event('change')); }
    }
  } catch (_) {}
}

function attachFormPersistence() {
  // Save on any input/change inside the form
  form.addEventListener('input',  saveFormState);
  form.addEventListener('change', saveFormState);
  // Also save when chips are clicked (they use click, not change)
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', saveFormState);
  });
}

// ── Init ───────────────────────────────────────────────────────
initChips();
initProviderCards();
initChildrenToggle();
restoreFormState();
attachFormPersistence();

// Set today as min date for departure
const today = new Date().toISOString().split('T')[0];
document.getElementById('departure_date').min = today;
document.getElementById('return_date').min    = today;
