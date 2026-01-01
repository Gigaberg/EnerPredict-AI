/* js/app.js
   Unified app script for appliances, solar, dashboard, nav helpers and small shared UI pieces.
   Drop this into your project (replace or merge with the existing file).
*/

document.addEventListener("DOMContentLoaded", () => {

  /* --------- Config / Helpers --------- */
  const STORAGE_KEY_APPLIANCES = 'aires_appliances_v1';
  const STORAGE_KEY_FEATURE_ORDER = 'aires_feature_order_v1';

  function apiBase() {
    return (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://localhost:8000'
      : '';
  }

  function el(id) { return document.getElementById(id); }
  function qsel(selector) { return document.querySelector(selector); }

  /* Safe fetch wrapper */
  async function safeFetch(url, options = {}) {
    try {
      const res = await fetch(url, options);
      if (!res.ok) {
        const txt = await res.text().catch(()=>null);
        const msg = txt || `HTTP ${res.status}`;
        throw new Error(msg);
      }
      return await res.json().catch(()=>null);
    } catch (err) {
      console.error('safeFetch error', err);
      throw err;
    }
  }

  /* --------- Theme toggle (light/dark) - shared, non-intrusive --------- */
  (function initThemeToggle(){
    // only add toggle if a container exists or create on body
    try {
      const container = document.querySelector('.theme-toggle-container') || document.body;
      if (!document.getElementById('theme-toggle-btn')) {
        const btn = document.createElement('button');
        btn.id = 'theme-toggle-btn';
        btn.type = 'button';
        btn.setAttribute('aria-label','Toggle theme');
        btn.className = 'theme-toggle-btn';
        btn.innerText = '🌓';
        btn.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:9999;border-radius:8px;padding:8px;backdrop-filter:blur(4px);';
        btn.addEventListener('click', () => {
          const t = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
          document.documentElement.setAttribute('data-theme', t);
          localStorage.setItem('aires_theme', t);
        });
        // restore
        const saved = localStorage.getItem('aires_theme');
        if (saved) document.documentElement.setAttribute('data-theme', saved);
        container.appendChild(btn);
      }
    } catch (e) { console.warn('theme toggle init failed', e); }
  })();

  /* --------- Nav active link helper --------- */
  (function navActive(){
    try {
      const path = window.location.pathname.split('/').pop();
      document.querySelectorAll('.nav-links a, nav a').forEach(a=>{
        const href = (a.getAttribute('href') || '').split('/').pop();
        if (href === path || (href === 'index.html' && (!path || path === ''))){
          a.classList.add('active');
        } else a.classList.remove('active');
      });
    } catch (e) { /* no-op */ }
  })();


  /* ==========================
     Appliance manager
     - Add / remove / render
     - Save to localStorage under STORAGE_KEY_APPLIANCES
     - Calculate simple consumption & send to backend
     ========================== */
  (function initApplianceManager(){
    const listEl = el('appliance-list');
    const nameI = el('name');
    const powerI = el('power');
    const hoursI = el('hours');
    const qtyI = el('qty');
    const addBtn = el('add-btn');
    const calcLocal = el('calc-local');
    const sendBackend = el('send-backend');
    const resultCard = el('result-card');
    const summary = el('summary');

    if (!listEl) return; // appliance page not present

    function readAppliances(){
      try { return JSON.parse(localStorage.getItem(STORAGE_KEY_APPLIANCES) || '[]'); }
      catch(e){ return []; }
    }
    function saveAppliances(arr){
      localStorage.setItem(STORAGE_KEY_APPLIANCES, JSON.stringify(arr));
    }

    function makeRemoveButton(idx){
      const b = document.createElement('button');
      b.className = 'btn small remove-appliance';
      b.type = 'button';
      b.setAttribute('data-idx', String(idx));
      b.setAttribute('aria-label', `Remove appliance ${idx+1}`);
      b.innerText = 'Remove';
      return b;
    }

    function renderList(){
      const arr = readAppliances();
      listEl.innerHTML = '';
      if (arr.length === 0) {
        listEl.innerHTML = '<div class="help-small">No appliances yet. Add one below.</div>';
        return;
      }
      arr.forEach((a, idx) => {
        const block = document.createElement('div');
        block.className = 'field-block appliance-item';
        block.style.display = 'flex';
        block.style.justifyContent = 'space-between';
        block.style.alignItems = 'center';
        block.style.marginBottom = '8px';
        const left = document.createElement('div');
        left.innerHTML = `<strong>${escapeHtml(a.name)}</strong><div class="help-small">Power: ${a.power} W • Hours/day: ${a.hours} • Qty: ${a.qty}</div>`;
        const right = document.createElement('div');
        right.style.display = 'flex';
        right.style.gap = '8px';
        const rem = makeRemoveButton(idx);
        rem.addEventListener('click', () => {
          const arr = readAppliances();
          arr.splice(idx,1);
          saveAppliances(arr);
          renderList();
        });
        right.appendChild(rem);
        block.appendChild(left);
        block.appendChild(right);
        listEl.appendChild(block);
      });
    }

    addBtn && addBtn.addEventListener('click', (ev)=>{
      ev.preventDefault();
      const name = (nameI.value || '').trim();
      const power = Number(powerI.value) || 0;
      const hours = Number(hoursI.value) || 0;
      const qty = Number(qtyI.value) || 1;
      if (!name) { alert('Enter appliance name'); return; }
      const arr = readAppliances();
      arr.push({ name, power, hours, qty });
      saveAppliances(arr);
      nameI.value = ''; powerI.value = ''; hoursI.value = ''; qtyI.value = '1';
      renderList();
      if (resultCard && summary) {
        resultCard.style.display = 'block';
        summary.textContent = `Saved ${arr.length} appliance(s).`;
        setTimeout(()=>{ resultCard.style.display='none'; }, 1400);
      }
    });

    calcLocal && calcLocal.addEventListener('click', (ev)=>{
      ev.preventDefault();
      const arr = readAppliances();
      if (!arr.length) { alert('No appliances to calculate'); return; }
      // monthly consumption estimate (kWh) = sum(power W * hours/day * qty) / 1000 * 30
      const totalWhDay = arr.reduce((s,a)=> s + (Number(a.power||0) * Number(a.hours||0) * Number(a.qty||1)), 0);
      const dailyKwh = totalWhDay / 1000;
      const monthly = dailyKwh * 30;
      if (resultCard && summary) {
        resultCard.style.display='block';
        summary.innerHTML = `Estimated: <strong>${dailyKwh.toFixed(2)} kWh/day</strong> • <strong>${monthly.toFixed(2)} kWh/month</strong>`;
      } else {
        alert(`Estimated: ${dailyKwh.toFixed(2)} kWh/day • ${monthly.toFixed(2)} kWh/month`);
      }
    });

    sendBackend && sendBackend.addEventListener('click', async (ev)=>{
      ev.preventDefault();
      const arr = readAppliances();
      if (!arr.length) { alert('No appliances to send'); return; }
      try {
        const payload = {
          house_id: `ui_${Date.now()}`,
          date: (new Date()).toISOString().slice(0,10),
          appliance_usage: {},
          total_consumption_kwh: 0
        };
        const totalWhDay = arr.reduce((s,a)=> s + (Number(a.power||0) * Number(a.hours||0) * Number(a.qty||1)), 0);
        payload.total_consumption_kwh = (totalWhDay/1000) * 30; // monthly
        arr.forEach(a => payload.appliance_usage[a.name] = (Number(a.hours||0) * Number(a.qty||1)));
        const res = await safeFetch(`${apiBase()}/household/`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        if (resultCard && summary) {
          resultCard.style.display='block';
          summary.textContent = 'Sent to backend ✓ (inserted id: ' + (res && res.inserted_id ? res.inserted_id : 'n/a') + ')';
        } else {
          alert('Sent to backend ✓');
        }
      } catch (err) {
        alert('Failed to send to backend (see console)');
      }
    });

    // initial render
    renderList();

    // helper: simple XSS escape for innerHTML inserts
    function escapeHtml(s) {
      if (!s) return '';
      return s.replace(/[&<>"'`=\/]/g, function (c) {
        return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','/':'&#x2F;','`':'&#x60;','=':'&#x3D;'}[c];
      });
    }
  })();


  /* ==========================
     Solar page handlers
     - Local calculate
     - API calculate (POST /api/solar/)
     ========================== */
  (function initSolar(){
    const calcBtn = el('calc-solar');
    const apiBtn = el('api-solar');
    const dailyEl = el('daily-kwh');
    const sunEl = el('sun-hours');
    const panelEl = el('panel-watt');
    const out = el('solar-output');

    if (!calcBtn && !apiBtn) return;

    function calculateLocal(){
      const daily = Number(dailyEl.value) || 0;
      const sun = Number(sunEl.value) || 0;
      const panel = Number(panelEl ? panelEl.value : 400) || 400;
      if (daily <= 0 || sun <= 0) {
        if (out) out.innerHTML = '<div class="help-small" style="color:#b00">Enter daily consumption & sun hours.</div>';
        return;
      }
      const eff = 0.75; // system efficiency
      const neededWh = daily * 1000;
      const panelDailyWh = panel * sun * eff;
      const panels = Math.ceil(neededWh / panelDailyWh);
      if (out) {
        out.innerHTML = `<div>Panels: <strong>${panels}</strong> • Estimated generation: <strong>${((panelDailyWh*panels)/1000).toFixed(2)} kWh/day</strong></div>`;
      } else {
        alert(`Panels: ${panels} • Estimated generation: ${((panelDailyWh*panels)/1000).toFixed(2)} kWh/day`);
      }
    }

    calcBtn && calcBtn.addEventListener('click', (e)=>{ e.preventDefault(); calculateLocal(); });

    apiBtn && apiBtn.addEventListener('click', async (e)=>{
      e.preventDefault();
      const daily = Number(dailyEl.value) || 0;
      const sun = Number(sunEl.value) || 0;
      const panel = Number(panelEl ? panelEl.value : 400) || 400;
      if (daily <= 0 || sun <= 0) {
        if (out) out.innerHTML = '<div class="help-small" style="color:#b00">Enter daily consumption & sun hours.</div>';
        return;
      }
      try {
        const res = await safeFetch(`${apiBase()}/api/solar/`, {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ daily_kwh: daily, sun_hours: sun, panel_watt: panel })
        });
        if (out) {
          out.innerHTML = `<div>Panels: <strong>${res.panels_required}</strong> • Estimated day gen: <strong>${res.estimated_daily_generation_kwh || 'n/a'} kWh</strong></div>`;
        } else {
          alert(`Panels: ${res.panels_required}`);
        }
      } catch (err) {
        if (out) out.innerHTML = `<div class="help-small" style="color:#b00">Error: ${err.message}</div>`;
      }
    });

  })();


  /* ==========================
     Dashboard helper: fetch history and show friendly fallback
     - Expects an element with id 'dashboard-history' (optional)
     ========================== */
  (function initDashboard(){
    const container = el('dashboard-history');
    if (!container) return;

    async function loadHistory() {
      let history = [];
      try {
        history = await safeFetch(`${apiBase()}/predict/history`);
      } catch (e) {
        // fallback to localStorage from predict.js if present
        try { history = JSON.parse(localStorage.getItem('aires_predictions') || '[]'); } catch(e) { history = []; }
      }
      render(history);
    }

    function render(history){
      container.innerHTML = '';
      if (!history || history.length === 0) {
        container.innerHTML = '<div class="help-small">No historical predictions yet — run a prediction to populate this dashboard.</div>';
        return;
      }
      // Render a simple table (compact)
      const table = document.createElement('table');
      table.className = 'table';
      const thead = document.createElement('thead');
      thead.innerHTML = '<tr><th>Date</th><th>House ID</th><th>Predicted kWh</th></tr>';
      table.appendChild(thead);
      const tbody = document.createElement('tbody');
      history.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${escapeHtml(item.date || '')}</td><td>${escapeHtml(item.house_id || item.id || '')}</td><td>${escapeHtml(String(item.predicted_kwh || item.total_consumption_kwh || '—'))}</td>`;
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      container.appendChild(table);
    }

    loadHistory();

    // helper escape
    function escapeHtml(s) {
      if (!s) return '';
      return s.replace(/[&<>"'`=\/]/g, function (c) {
        return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','/':'&#x2F;','`':'&#x60;','=':'&#x3D;'}[c];
      });
    }

  })();


  /* --------- Misc small helpers (exposed to page if needed) --------- */
  // Export some utilities to global for quick debugging in console
  window.AIRES = window.AIRES || {};
  window.AIRES.apiBase = apiBase;
  window.AIRES.safeFetch = safeFetch;
/* Dashboard charts init (requires Chart.js to be loaded on page) */
/* Dashboard charts init (updated to match dashboard.html ids: pieChart & barChart) */
(function initDashboardCharts(){
  const pieCanvas = document.getElementById('pieChart');
  const barCanvas = document.getElementById('barChart');

  // If neither canvas exists, nothing to do.
  if (!pieCanvas && !barCanvas) return;

  async function loadAndRender(){
    let history = [];
    try {
      history = await safeFetch(`${apiBase()}/predict/history`);
    } catch (e) {
      try { history = JSON.parse(localStorage.getItem('aires_predictions') || '[]'); } catch (err) { history = []; }
    }

    // If no history, show simple dummy data so charts are visible while developing.
    const hasHistory = Array.isArray(history) && history.length > 0;

    // --- Prepare bar (monthly) chart data ---
    let labels = [];
    let series = [];
    if (hasHistory) {
      const sorted = history.slice().sort((a,b) => new Date(a.date || a.timestamp || 0) - new Date(b.date || b.timestamp || 0));
      labels = sorted.map(h => (h.date || (h.timestamp ? new Date(h.timestamp).toISOString().slice(0,10) : '')) || '-');
      series = sorted.map(h => Number(h.predicted_kwh ?? h.total_consumption_kwh ?? h.estimated_kwh ?? 0));
    } else {
      // Dummy monthly trend
      labels = ['Jan','Feb','Mar','Apr','May','Jun'];
      series = [120,135,128,142,150,138];
    }

    // Render bar/line chart on barCanvas
    try {
      if (barCanvas) {
        const ctxBar = barCanvas.getContext('2d');
        if (barCanvas._chart) barCanvas._chart.destroy();
        barCanvas._chart = new Chart(ctxBar, {
          type: 'line',
          data: {
            labels: labels,
            datasets: [{
              label: 'Predicted kWh',
              data: series,
              fill: true,
              tension: 0.25,
              pointRadius: 3
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
              x: { display: true },
              y: { beginAtZero: true, title: { display: true, text: 'kWh' } }
            }
          }
        });
      }
    } catch (err) {
      console.error('Error rendering monthly/bar chart', err);
    }

    // --- Prepare pie (appliance) chart data ---
    let labelsA = [];
    let dataA = [];
    if (hasHistory) {
      const agg = {};
      history.forEach(h => {
        const usage = h.appliance_usage || h.appliances || h.breakdown || h.appliance_breakdown;
        if (usage && typeof usage === 'object') {
          Object.entries(usage).forEach(([k,v]) => {
            const val = Number(v) || 0;
            agg[k] = (agg[k] || 0) + val;
          });
        }
      });
      labelsA = Object.keys(agg);
      dataA = labelsA.map(k => agg[k]);
    } else {
      // Dummy appliance breakdown
      labelsA = ['Fridge','AC','Lights','TV','Other'];
      dataA = [35,25,20,10,10];
    }

    // Render pie chart on pieCanvas
    try {
      if (pieCanvas) {
        const ctxPie = pieCanvas.getContext('2d');
        if (pieCanvas._chart) pieCanvas._chart.destroy();
        pieCanvas._chart = new Chart(ctxPie, {
          type: 'pie',
          data: {
            labels: labelsA,
            datasets: [{
              data: dataA
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: true
          }
        });
      }
    } catch (err) {
      console.error('Error rendering pie chart', err);
    }
  }

  // Kick off rendering
  loadAndRender();
})();



});
