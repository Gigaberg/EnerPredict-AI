// js/predict.js  (enhanced: validation, autofill, UI polish, vector debug, responsive tweaks)
//
// IMPORTANT: set API_BASE to your backend origin if different
const API_BASE = "http://localhost:8000"; // <-- change if your backend runs elsewhere

const MODELS_URL = API_BASE + "/predict/models";
const FEATURE_ORDER_URL = API_BASE + "/predict/feature_order";
const PREDICT_URL = API_BASE + "/predict/";

// --- default per-appliance wattages used when user supplies "count" mode ---
const DEFAULT_WATTS = {
  "Fan": 70,
  "Refrigerator": 150,
  "AirConditioner": 1200,
  "Television": 100,
  "Monitor": 30,
  "MotorPump": 500
};

// ---------- Dark mode toggle + persistence ----------
// Place this near the top of your main frontend JS file (predict.js).
(function(){
  const STORAGE_KEY = "enerpredict_theme"; // "dark"|"light"|null
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

  function applyTheme(name){
    if(name === "dark"){
      document.body.classList.add("dark-theme");
    } else {
      document.body.classList.remove("dark-theme");
    }
  }

  // read persisted value or use system pref
  const saved = localStorage.getItem(STORAGE_KEY);
  const initial = saved ? saved : (prefersDark ? "dark" : "light");
  applyTheme(initial);

  // small helper to create toggle button in nav (if nav exists)
  function createThemeToggle(){
    const nav = document.querySelector(".nav");
    if(!nav) return;

    // don't insert twice
    if(document.querySelector(".theme-toggle-btn")) return;

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "theme-toggle-btn";
    btn.setAttribute("aria-pressed", initial === "dark" ? "true" : "false");
    btn.title = "Toggle dark / light mode";

    // inline SVG icons (moon + sun)
    const moon = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    const sun = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.6"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

    // display either icon depending on theme
    const iconWrap = document.createElement("span");
    iconWrap.style.display = "inline-flex";
    iconWrap.innerHTML = (initial === "dark") ? sun : moon;

    const label = document.createElement("span");
    label.textContent = initial === "dark" ? "Light" : "Dark";
    label.style.fontSize = "13px";

    btn.appendChild(iconWrap);
    btn.appendChild(label);

    // style (if you prefer manual placement, you can move the append)
    btn.style.marginLeft = "14px";

    btn.addEventListener("click", () => {
      const isDark = document.body.classList.toggle("dark-theme");
      const newTheme = isDark ? "dark" : "light";
      localStorage.setItem(STORAGE_KEY, newTheme);
      btn.setAttribute("aria-pressed", isDark ? "true" : "false");

      // swap icon + label
      iconWrap.innerHTML = isDark ? sun : moon;
      label.textContent = isDark ? "Light" : "Dark";
    });

    // append to nav links area (or nav itself)
    const right = nav.querySelector(".nav-links") || nav;
    right.appendChild(btn);
  }

  // try to create toggle on DOM ready
  if(document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", createThemeToggle);
  } else {
    createThemeToggle();
  }
})();


// small inline SVG icons for appliances (kept tiny and inline to avoid extra assets)
const ICON_SVGS = {
  "Fan": `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2v4" stroke="#ff8c00" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 18v4" stroke="#ff8c00" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M4 12h4" stroke="#ff8c00" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M16 12h4" stroke="#ff8c00" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="3.2" stroke="#ff8c00" stroke-width="1.6"/></svg>`,
  "Refrigerator": `<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><rect x="6" y="3" width="12" height="18" rx="2" stroke="#2a9d8f" stroke-width="1.4" /><path d="M10 7h4" stroke="#2a9d8f" stroke-width="1.4" stroke-linecap="round"/></svg>`,
  "AirConditioner": `<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><rect x="3" y="5" width="18" height="10" rx="2" stroke="#2266aa" stroke-width="1.4"/><path d="M6 9h12" stroke="#2266aa" stroke-width="1.4" stroke-linecap="round"/></svg>`,
  "Television": `<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><rect x="3" y="5" width="18" height="12" rx="1.5" stroke="#7b61ff" stroke-width="1.4"/><path d="M8 21l4-3 4 3" stroke="#7b61ff" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  "Monitor": `<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><rect x="4" y="4" width="16" height="11" rx="1.2" stroke="#f39c12" stroke-width="1.4"/><path d="M12 19v-3" stroke="#f39c12" stroke-width="1.4" stroke-linecap="round"/></svg>`,
  "MotorPump": `<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="8" cy="12" r="3" stroke="#d62828" stroke-width="1.4"/><path d="M11 12h7" stroke="#d62828" stroke-width="1.4" stroke-linecap="round"/></svg>`
};

//
// DOM refs
//
const modelSelect = document.getElementById("modelSelect");
const modelDescription = document.getElementById("modelDescription");
const dynamicFields = document.getElementById("dynamicFields");
const predictForm = document.getElementById("predictForm");
const loadingIndicator = document.getElementById("loadingIndicator");
const resultArea = document.getElementById("resultArea");
const historyCanvas = document.getElementById("predictionHistoryChart");
const autoFillToggle = document.getElementById("autoFillToggle");
const suggestFixesBtn = document.getElementById("suggestFixes");
const importBtn = document.getElementById("import-appliances-btn");
const suggestNote = document.getElementById("suggestNote");
const clearHistoryBtn = document.getElementById("clear-history");

let featureOrder = null;
let models = {};
let chart = null;

function el(id){ return document.getElementById(id); }
function showLoading(on=true){
  if(on){ loadingIndicator.innerHTML = '<span class="spinner"></span>'; el("get-prediction").classList.add("disabled"); }
  else { loadingIndicator.innerHTML = ""; el("get-prediction").classList.remove("disabled"); }
}
function showError(msg){ resultArea.innerHTML = `<div style="color:#b00;font-weight:700">${msg}</div>`; }
function showResult(html){ resultArea.innerHTML = html; }

//
// Chart & history
//
function initChart(){
  try{
    if(!historyCanvas) return;
    const ctx = historyCanvas.getContext("2d");
    chart = new Chart(ctx, {
      type: "line",
      data: { labels: [], datasets: [{ label: "Predicted kWh", data: [], fill:false, tension:0.2, borderColor:"#ff8c00" }] },
      options: { scales: { x: { display:false }, y: { beginAtZero:true } }, plugins: { legend: { display:false } } }
    });
    loadHistoryToChart();
  }catch(e){console.warn(e);}
}
function saveHistory(item){
  try{
    const key="prediction_history_v2";
    const arr = JSON.parse(localStorage.getItem(key) || "[]");
    arr.unshift(item);
    localStorage.setItem(key, JSON.stringify(arr.slice(0,30)));
    loadHistoryToChart();
  }catch(e){console.warn(e);}
}
function loadHistoryToChart(){
  try{
    const arr = JSON.parse(localStorage.getItem("prediction_history_v2") || "[]");
    if(!chart) return;
    const labels = arr.map(r => new Date(r.timestamp).toLocaleTimeString()).reverse();
    const data = arr.map(r => Number(r.predicted_value_kwh) || 0).reverse();
    chart.data.labels = labels;
    chart.data.datasets[0].data = data;
    chart.update();
  } catch(e){console.warn(e);}
}
function clearHistory(){ localStorage.removeItem("prediction_history_v2"); loadHistoryToChart(); }

//
// Field helpers (validation / suggestions)
// We implement a small ruleset for ranges and required checks.
//
const FIELD_RULES = {
  // fieldName: { required:bool, min: number|null, max:number|null, step: 'int'|'any' }
  "MonthlyHours": {required:true, min:0, max:744, step:'int'},         // max 31*24=744
  "TariffRate": {required:true, min:0, max:200, step:'any'},
  "SolarGeneration_kWh": {required:false, min:0, max:10000, step:'any'},
  "GridConsumption_kWh": {required:false, min:0, max:20000, step:'any'},
  "EnergySold_kWh": {required:false, min:0, max:20000, step:'any'},
  "NetBill": {required:false, min:0, max:1e7, step:'any'},
  "Fan": {required:false, min:0, max:100, step:'int'},
  "Refrigerator": {required:false, min:0, max:50, step:'int'},
  "AirConditioner": {required:false, min:0, max:20, step:'int'},
  "Television": {required:false, min:0, max:20, step:'int'},
  "Monitor": {required:false, min:0, max:20, step:'int'},
  "MotorPump": {required:false, min:0, max:10, step:'int'}
};

function createValidationNote(elNode, msg, isError=true){
  let note = elNode.parentElement.querySelector(".field-note");
  if(!note){
    note = document.createElement("div");
    note.className = "field-note help-small";
    elNode.parentElement.appendChild(note);
  }
  note.textContent = msg;
  note.style.color = isError ? "#b00" : "#666";
}
function clearValidationNote(elNode){
  const note = elNode.parentElement.querySelector(".field-note");
  if(note) note.textContent = "";
}

//
// Create input fields dynamically based on feature_order
//
function createFieldForFeature(name){
  const labelText = name.replace(/_/g," ");
  const wrapper = document.createElement("div");
  wrapper.className = "field-block";

  // Skip one-hot city columns (handled separately)
  if (name.startsWith("City_")) {
    wrapper.style.display = "none";
    return wrapper;
  }

  const label = document.createElement("label");
  label.htmlFor = name;
  label.textContent = labelText;
  wrapper.appendChild(label);

  // Choose input type heuristics (appliances get special UI)
  let input = document.createElement("input");
  input.id = name;
  input.name = name;

  const applianceNames = ["Fan","Refrigerator","AirConditioner","Television","Monitor","MotorPump"];

  // For appliance fields we'll show an icon + mode selector
  if (applianceNames.includes(name)) {
    // create a container row with appliance-row class
    const row = document.createElement("div");
    row.className = "appliance-row";

    // icon span
    const iconWrap = document.createElement("div");
    iconWrap.className = "appliance-icon";
    iconWrap.innerHTML = ICON_SVGS[name] || "";
    iconWrap.style.flex = "0 0 32px";
    iconWrap.style.display = "flex";
    iconWrap.style.alignItems = "center";
    iconWrap.style.justifyContent = "center";
    row.appendChild(iconWrap);

    // input for either count or power
    input.type = "number";
    input.step = "1";
    input.placeholder = "e.g. 2 (count) or 140 (power in W)";
    input.style.flex = "1 1 auto";
    input.style.minWidth = "150px";
    row.appendChild(input);

    // mode select (Count | Power)
    const modeSel = document.createElement("select");
    modeSel.id = name + "__mode";
    modeSel.style.minWidth = "120px";
    modeSel.innerHTML = `<option value="count">Count</option><option value="power">Power (W)</option>`;
    row.appendChild(modeSel);

    wrapper.appendChild(row);

    // hint area
    const hint = document.createElement("div");
    hint.className = "help-small";
    hint.style.marginTop = "6px";
    hint.style.color = "#666";
    wrapper.appendChild(hint);

    // update hint live when input or mode changes
    function updateApplianceHint(){
      const mode = modeSel.value;
      const valRaw = input.value;
      const val = Number(valRaw);
      const defaultW = DEFAULT_WATTS[name] || 0;
      if(mode === "count"){
        if(valRaw === "" || isNaN(val)) hint.textContent = `Enter number of ${labelText.toLowerCase()} (will be converted to estimated power ${defaultW}W each).`;
        else hint.textContent = `Estimated power: ${Math.round(val * defaultW)} W ( ${val} × ${defaultW}W ) — you can switch to "Power (W)" to enter exact watts.`;
      } else {
        hint.textContent = `Enter total power for ${labelText.toLowerCase()} in Watts (W).`;
      }
      validateField(name, input);
    }

    input.addEventListener("input", updateApplianceHint);
    modeSel.addEventListener("change", updateApplianceHint);
    // initialize hint
    updateApplianceHint();

    return wrapper;
  }

  // Non-appliance fields: general numeric or text
  if (["MonthlyHours","TariffRate","SolarGeneration_kWh","GridConsumption_kWh","EnergySold_kWh","NetBill","avg_power_per_appliance","total_appliance_power"].includes(name)) {
    input.type = "number"; input.step = "any";
    if (name === "MonthlyHours") input.placeholder = "e.g. 240 (approx 8 hours/day × 30)";
    if (name === "TariffRate") input.placeholder = "e.g. 12 (₹ / kWh)";
    if (name === "GridConsumption_kWh" || name === "SolarGeneration_kWh" || name === "EnergySold_kWh") input.placeholder = "value in kWh";
    if (name === "NetBill") input.placeholder = "Total bill amount (₹)";
  } else if (["appliance_count","Month_num"].includes(name)) {
    input.type = "number"; input.step = "1";
  } else {
    input.type = "text";
  }

  wrapper.appendChild(input);

  const hint = document.createElement("div");
  hint.className = "help-small";
  hint.style.marginTop = "6px";
  hint.style.color = "#666";

  if (name === "MonthlyHours") hint.textContent = "Typical: 240–780 (enter hours per month appliance(s) are used).";
  else if (name === "TariffRate") hint.textContent = "Enter your tariff in ₹ per kWh (example: 12).";
  else hint.textContent = "";

  wrapper.appendChild(hint);

  input.addEventListener("input", () => {
    validateField(name, input);
    if(autoFillToggle && autoFillToggle.checked) applyAutoFill();
  });

  return wrapper;
}



function validateField(name, inputEl){
  const rules = FIELD_RULES[name];
  if(!rules) { clearValidationNote(inputEl); return true; }
  const val = inputEl.value;
  if(rules.required && (val === "" || val === null)){
    createValidationNote(inputEl, "This field is recommended (you may leave 0 if unknown).");
    return false;
  }
  if(val === "" || val === null){ clearValidationNote(inputEl); return true; }
  const n = Number(val);
  if(isNaN(n)){
    createValidationNote(inputEl, "Enter a valid number.");
    return false;
  }
  if(rules.min !== null && n < rules.min){
    createValidationNote(inputEl, `Value must be ≥ ${rules.min}`);
    return false;
  }
  if(rules.max !== null && n > rules.max){
    createValidationNote(inputEl, `Value seems high (max suggested ${rules.max})`, true);
    return true; // warning but not block
  }
  // ok
  createValidationNote(inputEl, "OK", false);
  setTimeout(()=>clearValidationNote(inputEl), 900);
  return true;
}

//
// Build dynamic form from feature_order
//
function buildDynamicForm(){
  dynamicFields.innerHTML = "";
  if(!featureOrder || !Array.isArray(featureOrder)){
    dynamicFields.innerHTML = "<div style='color:#b00'>Feature order missing — backend not ready.</div>";
    return;
  }

  // If City one-hot columns exist, create single City_code control
  const hasCity = featureOrder.some(f => f.startsWith("City_"));
  if(hasCity){
    const cw = document.createElement("div"); cw.className="field-block";
    const cl = document.createElement("label"); cl.htmlFor="City_code"; cl.textContent="City (select)";
    cw.appendChild(cl);
    const sel = document.createElement("select"); sel.id="City_code"; sel.name="City_code";
    [["1","City A"],["2","City B"],["3","City C"],["4","City D"]].forEach(o=>{
      const opt=document.createElement("option"); opt.value=o[0]; opt.text=o[1]; sel.appendChild(opt);
    });
    cw.appendChild(sel);
    const hint=document.createElement("div"); hint.className="help-small"; hint.textContent="Select the city; this will be converted to one-hot features.";
    cw.appendChild(hint);
    dynamicFields.appendChild(cw);
  }

  // create a collapsible details for appliances
  const applianceNames = ["Fan","Refrigerator","AirConditioner","Television","Monitor","MotorPump"];
  const details = document.createElement("details");
  details.open = false;
  details.style.marginTop = "10px";
  details.style.padding = "8px";
  details.style.borderRadius = "8px";
  details.style.background = "#fbfbfb";
  details.style.border = "1px solid #f0f0f0";

  const summary = document.createElement("summary");
  summary.textContent = "Appliance details (expand)";
  summary.style.fontWeight = "700";
  summary.style.cursor = "pointer";
  summary.style.marginBottom = "8px";
  details.appendChild(summary);

  const applianceContainer = document.createElement("div");
  applianceContainer.id = "appliance-list";

  // build appliance fields first
  for(const f of featureOrder){
    if(applianceNames.includes(f)){
      const node = createFieldForFeature(f);
      applianceContainer.appendChild(node);
    }
  }

  // append the appliance container to the details
  details.appendChild(applianceContainer);
  dynamicFields.appendChild(details);

  // build input for each non-city, non-appliance feature
  for(const f of featureOrder){
    if(f.startsWith("City_")) continue;
    if(applianceNames.includes(f)) continue;
    const node = createFieldForFeature(f);
    dynamicFields.appendChild(node);
  }

  // add feature-vector debug toggle & container
  const debugRow = document.createElement("div"); debugRow.className="field-block";
  const dbgToggle = document.createElement("button"); dbgToggle.type="button"; dbgToggle.className="btn"; dbgToggle.textContent="Show Feature Vector";
  const dbgContainer = document.createElement("pre"); dbgContainer.id="featureVectorDebug"; dbgContainer.style.display="none"; dbgContainer.style.background="#f6f6f6"; dbgContainer.style.padding="8px"; dbgContainer.style.borderRadius="6px"; dbgContainer.style.marginTop="8px";
  dbgToggle.addEventListener("click", ()=>{
    if(dbgContainer.style.display==="none"){ dbgContainer.style.display="block"; dbgToggle.textContent="Hide Feature Vector"; dbgContainer.textContent = JSON.stringify(buildFeaturesArray(), null, 2); }
    else { dbgContainer.style.display="none"; dbgToggle.textContent="Show Feature Vector"; }
  });
  debugRow.appendChild(dbgToggle);
  debugRow.appendChild(dbgContainer);
  dynamicFields.appendChild(debugRow);
}

//
// Auto-fill rules (smarter)
// - compute total_appliance_power from avg*count if missing
// - compute NetBill from GridConsumption_kWh * TariffRate
// - suggest MonthlyHours default if blank (use small heuristic)
function applyAutoFill(force=false){
  // appliances
  const total = el("total_appliance_power"); const avg = el("avg_power_per_appliance"); const count = el("appliance_count");
  if(total && (!total.value || force) && avg && count && avg.value && count.value){
    const val = Number(avg.value) * Number(count.value);
    if(!isNaN(val) && val>0) total.value = Math.round(val*100)/100;
  }
  // NetBill
  const nb = el("NetBill"); const g = el("GridConsumption_kWh"); const t = el("TariffRate");
  if(nb && (!nb.value || force) && g && t && g.value){
    const calc = Number(g.value) * (Number(t && t.value ? Number(t.value) : 0));
    if(!isNaN(calc)) nb.value = Math.round(calc*100)/100;
  }
  // MonthlyHours suggestion: if blank, suggest 240 (8h/day*30) or 300 if AC present
  const mh = el("MonthlyHours");
  if(mh && (!mh.value || force)){
    const ac = el("AirConditioner"); const anyAC = ac && Number(ac.value) > 0;
    mh.value = anyAC ? 300 : 240;
  }
  // compute avg if missing: avg = total/count
  if(avg && (!avg.value || force) && total && count && count.value){
    const c = Number(count.value);
    if(c>0){ const a = Number(total.value)/c; if(!isNaN(a)) avg.value = Math.round(a*100)/100; }
  }
  // after autofill run validation
  document.querySelectorAll("#dynamicFields input").forEach(i => {
    const name = i.id; if(name) validateField(name,i);
  });
}

//
// Build features array in exact order (converting City_code to one-hot)
//
function getInputValueRaw(id){
  const e = el(id); if(!e) return null;
  if(e.type === "number" || e.tagName.toLowerCase() === "input" && e.type === "text"){ return e.value === "" ? null : e.value; }
  return e.value;
}
function buildFeaturesArray(){
  if(!featureOrder) throw new Error("feature_order missing");
  const arr = [];

  // read city code
  let cityCode = Number(getInputValueRaw("City_code"));
  if(isNaN(cityCode)) cityCode = 1;
  const map = {1:"A",2:"B",3:"C",4:"D"}; const letter = map[cityCode] || "A";

  for(const f of featureOrder){
    if(f.startsWith("City_")){
      const suf = f.split("_").pop();
      arr.push(suf === letter ? 1 : 0);
      continue;
    }

    // appliance names mapping: if a appliance field has a companion mode select we treat accordingly
    const applianceNames = ["Fan","Refrigerator","AirConditioner","Television","Monitor","MotorPump"];

    if(applianceNames.includes(f)){
      const raw = getInputValueRaw(f);
      const modeEl = el(f + "__mode");
      const mode = modeEl ? modeEl.value : "count";
      if(raw === null || raw === "") { arr.push(0); continue; }
      const v = Number(raw);
      if(isNaN(v)){ arr.push(0); continue; }
      if(mode === "count"){
        const defaultW = DEFAULT_WATTS[f] || 0;
        arr.push(Number(Math.round((v * defaultW) * 100)/100));
      } else {
        // user supplied power directly
        arr.push(Number(v));
      }
      continue;
    }

    if(f === "NetBill"){
      const nb = getInputValueRaw("NetBill");
      if(nb !== null && nb !== "") { arr.push(Number(nb)); continue; }
      const grid = Number(getInputValueRaw("GridConsumption_kWh")) || 0;
      const tariff = Number(getInputValueRaw("TariffRate")) || 0;
      arr.push(Number(Math.round((grid*tariff) * 100)/100));
      continue;
    }

    const raw = getInputValueRaw(f);
    if(raw !== null && raw !== "") { const n = Number(raw); arr.push(isNaN(n) ? 0 : n); continue; }

    // aliases fallback
    const aliases = {"total_appliance_power":["total_appliance_power","TotalAppliancePower"], "appliance_count":["appliance_count"], "avg_power_per_appliance":["avg_power_per_appliance"]};
    if(aliases[f]){
      let found = null;
      for(const a of aliases[f]){ const v = getInputValueRaw(a); if(v !== null && v !== "") { found = v; break; } }
      arr.push(found !== null ? Number(found) : 0);
      continue;
    }

    arr.push(0);
  }

  return arr;
}

//
// UI: pretty result card with gauge + delta vs last prediction
//
function showPrettyResult(value, model, houseId){
  // fetch last value from history for delta
  const hist = JSON.parse(localStorage.getItem("prediction_history_v2") || "[]");
  const last = (hist && hist.length>0) ? Number(hist[0].predicted_value_kwh) : null;
  const v = Number(value);
  const delta = last !== null ? (v - last) : null;
  // decide color
  let color = "#ff8c00"; // orange default
  if(v <= 100) color = "#2a9d8f"; // green
  else if(v > 500) color = "#d62828"; // red high usage

  // gauge simple CSS circle using conic-gradient
  const gaugePct = Math.min(100, Math.round((v / Math.max(1, (last||v))) * 50 + 10)); // heuristic
  const gaugeHtml = `<div style="width:88px;height:88px;border-radius:50%;background:conic-gradient(${color} ${gaugePct}%, #eee ${gaugePct}%);display:inline-block;margin-right:12px;vertical-align:middle"></div>`;

  const deltaHtml = delta !== null ? `<div style="font-size:13px;color:${delta>=0? '#b00':'#2a9d8f'};margin-top:6px">${delta>=0? '▲':'▼'} ${Math.abs(delta).toFixed(2)} kWh vs last</div>` : "";

  showResult(`<div style="display:flex;align-items:center;gap:12px">
      ${gaugeHtml}
      <div>
        <div style="font-size:20px;font-weight:800;color:${color}">${isNaN(v)? value: v.toFixed(2)} kWh</div>
        <div class="small-muted">Model: ${model} • House: ${houseId}</div>
        ${deltaHtml}
      </div>
    </div>`);
}

//
// Submit prediction
//
async function submitPrediction(e){
  if(e && e.preventDefault) e.preventDefault();
  // run validation for required fields
  let ok = true;
  document.querySelectorAll("#dynamicFields input").forEach(inp=>{
    const name = inp.id;
    if(name) { const r = validateField(name, inp); if(r===false) ok=false; }
  });
  if(!ok){
    showError("Please fix highlighted fields or fill recommended values.");
    return;
  }

  showLoading(true);
  try{
    applyAutoFill(); // final autofill
    const features = buildFeaturesArray();
    if(!Array.isArray(features) || features.length !== featureOrder.length){
      throw new Error(`Feature vector length mismatch: expected ${featureOrder.length} got ${features.length}`);
    }
    const payload = { house_id: `ui_${Date.now()}`, model: modelSelect.value, features, meta:{} };
    const resp = await fetch(PREDICT_URL, { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload) });
    const body = await resp.json().catch(()=>null);
    if(!resp.ok){ showError(body && body.detail ? body.detail : `Prediction failed (${resp.status})`); return; }

    // show pretty result
    showPrettyResult(body.predicted_value_kwh, body.model, body.house_id);

    // update feature vector debug if visible
    const dbg = document.getElementById("featureVectorDebug");
    if(dbg && dbg.style.display !== "none") dbg.textContent = JSON.stringify(features, null, 2);

    // save history
    saveHistory({ predicted_value_kwh: body.predicted_value_kwh, model: body.model, timestamp: body.timestamp || new Date().toISOString(), features: body.features });

  }catch(err){
    console.error(err);
    showError(err.message || "Prediction failed");
  }finally{
    showLoading(false);
  }
}

//
// Import appliances helper (reads localStorage: 'aires_appliances_v1')
//
function importAppliances(){
  try{
    const raw = localStorage.getItem("aires_appliances_v1");
    if(!raw){ alert("No appliances found in local storage"); return; }
    const list = JSON.parse(raw);
    let total=0, count=0;
    list.forEach(it => { const p=Number(it.power||0); const q=Number(it.qty||1); total += (isNaN(p)?0:p) * (isNaN(q)?1:q); count += (isNaN(q)?1:q); });
    if(el("total_appliance_power")) el("total_appliance_power").value = Math.round(total*100)/100;
    if(el("appliance_count")) el("appliance_count").value = count || list.length;
    if(el("avg_power_per_appliance")) el("avg_power_per_appliance").value = count ? Math.round((total/count)*100)/100 : 0;
    if(document.getElementById("import-appliances-hint")) document.getElementById("import-appliances-hint").textContent = "Imported ✓";
    applyAutoFill(true);
    setTimeout(()=>{ if(document.getElementById("import-appliances-hint")) document.getElementById("import-appliances-hint").textContent = ""; }, 1500);
  }catch(e){ alert("Failed to import appliances"); console.error(e); }
}

//
// Initialization: fetch models & feature order
//
async function init(){
  showLoading(false);
  try{
    const [mres, fres] = await Promise.all([ fetch(MODELS_URL).catch(()=>null), fetch(FEATURE_ORDER_URL).catch(()=>null) ]);

    if(mres && mres.ok){
      const jm = await mres.json();
      models = jm.models || {};
      populateModelSelect(models);
    } else {
      models = { xgb:"XGBoost Regressor", rf:"Random Forest", linear:"Linear Regression" };
      populateModelSelect(models);
      modelDescription.innerText = "Model list fallback (backend unreachable).";
    }

    if(fres && fres.ok){
      const jf = await fres.json();
      featureOrder = jf.feature_order || jf;
    } else {
      featureOrder = ["Fan","Refrigerator","AirConditioner","Television","Monitor","MotorPump","MonthlyHours","SolarGeneration_kWh","GridConsumption_kWh","EnergySold_kWh","TariffRate","NetBill","City_City_A","City_City_B","City_City_C","City_City_D"];
    }

    buildDynamicForm();
    initChart();
    // events
    predictForm.addEventListener("submit", submitPrediction);
    suggestFixesBtn && suggestFixesBtn.addEventListener("click", ()=>{ applyAutoFill(true); showResult("<div style='color:#2266aa'>Autofill applied.</div>"); });
    autoFillToggle && autoFillToggle.addEventListener("change", ()=>{ suggestNote.textContent = autoFillToggle.checked ? "Auto-fill enabled." : "Auto-fill disabled."; if(autoFillToggle.checked) applyAutoFill(); });
    importBtn && importBtn.addEventListener("click", importAppliances);
    clearHistoryBtn && clearHistoryBtn.addEventListener("click", ()=>{ if(confirm("Clear local history?")){ clearHistory(); showResult("<div style='color:#666'>History cleared.</div>"); }});
  }catch(e){
    console.error(e);
    showError("Initialization failed — check console");
  }
}

function populateModelSelect(m){
  modelSelect.innerHTML = "";
  const keys = Object.keys(m);
  if(keys.length===0){ modelSelect.innerHTML = "<option value='xgb'>XGBoost</option>"; return; }
  keys.forEach(k => { const opt=document.createElement("option"); opt.value=k; opt.textContent = m[k]; modelSelect.appendChild(opt); });
  modelSelect.value = keys[0];
  modelDescription.innerText = `${m[modelSelect.value] || ""}`;
  modelSelect.addEventListener("change", ()=> modelDescription.innerText = `${m[modelSelect.value] || ""}`);
}

// run init on DOM ready
document.addEventListener("DOMContentLoaded", init);
