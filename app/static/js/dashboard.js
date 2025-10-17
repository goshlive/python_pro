/* --- Fungsi Helper --- */
// Meng-highlight tombol hari yang aktif: hari ini, besok, lusa
function setActiveDay(btn) {
  document.querySelectorAll('[data-day]').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}
// Mengambil token CSRF untuk method POST
function csrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}
// Meng-escape karakter khusus agar aman saat ditampilkan
function escapeHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

/* --- Menampilkan Rating Skor (leaderboard) --- */
// Ambil elemen pada daftar skor
const lbList = document.getElementById('leaderboard-list');

// Tampilkan daftar skor
function renderLeaderboard(items) {
  if (!lbList) return;
  if (!items || !items.length) {
    lbList.innerHTML = '<li class="list-group-item">Belum ada skor.</li>';
    return;
  }
  lbList.innerHTML = items.map(u => `
    <li class="list-group-item d-flex justify-content-between align-items-center">
      <span class="text-truncate">${escapeHtml(u.username)}</span>
      <span class="badge bg-primary rounded-pill">${u.score}</span>
    </li>
  `).join('');
}

// Ambil data skor dari database melalui route /api/leaderboard
async function fetchLeaderboard() {
  try {
    const r = await fetch('/api/leaderboard');
    if (!r.ok) return;
    const j = await r.json();
    renderLeaderboard(j.leaders || []);
  } catch (_) {}
}

/* --- Fungsi untuk Prakiraan Cuaca --- */
// Default kota: Denpasar (sesuai konfigurasi di file .env)
let selectedCity = { name: window.__DEFAULT_CITY__, lat: -8.65, lon: 115.2167 }; // default (Denpasar)
let forecast = null;

// Ambil elemen-elemen terkait cuaca
const cityInput = document.getElementById('city-input');
const citySuggest = document.getElementById('city-suggest');
const headerCity = document.getElementById('header-city');
const titleCity = document.getElementById('weather-title-city');
const details = document.getElementById('weather-details');

// Cari kota berdasarkan parameter q (nama kota)
async function searchCities(q) {
  if (!q || q.length < 2) return [];
  const url = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(q)}&count=8&language=id&format=json`;
  const r = await fetch(url);
  if (!r.ok) return [];
  const j = await r.json();
  return (j.results || []).map(c => ({
    name: `${c.name}${c.admin1 ? ', ' + c.admin1 : ''}${c.country ? ', ' + c.country : ''}`,
    lat: c.latitude, lon: c.longitude
  }));
}

// Render daftar kota yang muncul saat mengetik di input
function renderSuggestions(items) {
  if (!citySuggest) return;
  citySuggest.innerHTML = '';
  if (!items.length) { citySuggest.classList.add('d-none'); return; }
  items.forEach(item => {
    const a = document.createElement('button');
    a.type = 'button';
    a.className = 'list-group-item list-group-item-action';
    a.textContent = item.name;
    a.onclick = () => {
      selectedCity = item;
      if (cityInput) cityInput.value = item.name;
      citySuggest.classList.add('d-none');
      if (headerCity) headerCity.textContent = item.name.split(',')[0];
      if (titleCity) titleCity.textContent = item.name;
      loadForecast();
    };
    citySuggest.appendChild(a);
  });
  citySuggest.classList.remove('d-none');
}

// Event listener untuk input kota dan menampilkan kota yang disarankan
let typeTimer;
if (cityInput) {
  cityInput.addEventListener('input', () => {
    clearTimeout(typeTimer);
    typeTimer = setTimeout(async () => {
      const items = await searchCities(cityInput.value.trim());
      renderSuggestions(items);
    }, 200);
  });
}

// Sembunyikan saran kota saat klik di luar area input
document.addEventListener('click', (e) => {
  if (citySuggest && !citySuggest.contains(e.target) && e.target !== cityInput) {
    citySuggest.classList.add('d-none');
  }
});

// Ambil data prakiraan cuaca dari API Open-Meteo
async function loadForecast() {
  if (!details) return;
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${selectedCity.lat}&longitude=${selectedCity.lon}&hourly=temperature_2m,is_day&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto`;
  const r = await fetch(url);
  if (!r.ok) { details.innerHTML = `<div class="text-danger">Gagal memuat cuaca.</div>`; return; }
  forecast = await r.json();
  renderForecastDay(0);
}

// Tampilkan detail prakiraan cuaca untuk hari tertentu (offset: 0=hari ini, 1=besok, dst)
function renderForecastDay(offset) {
  if (!forecast || !details) return;
  const d = {
    date: forecast.daily.time[offset],
    tmax: forecast.daily.temperature_2m_max[offset],
    tmin: forecast.daily.temperature_2m_min[offset],
    wcode: forecast.daily.weathercode[offset],
  };
  let dayAvg = null, nightAvg = null;
  if (offset === 0 && forecast.hourly) {
    const temps = forecast.hourly.temperature_2m;
    const isDay = forecast.hourly.is_day;
    let dsum=0, dcount=0, nsum=0, ncount=0;
    for (let i=0;i<temps.length;i++) {
      if (isDay[i]===1) { dsum+=temps[i]; dcount++; } else { nsum+=temps[i]; ncount++; }
    }
    dayAvg = dcount? (dsum/dcount).toFixed(1): null;
    nightAvg = ncount? (nsum/ncount).toFixed(1): null;
  }
  details.innerHTML = `
    <div class="col-12 col-md-4">
      <div class="border rounded p-3 h-100">
        <div class="small text-muted mb-1">${new Date(d.date).toLocaleDateString('id-ID', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' })}</div>
        <div class="display-6">${Math.round(d.tmax)}°</div>
        <div class="text-muted">Tinggi / Rendah: ${Math.round(d.tmax)}° / ${Math.round(d.tmin)}°</div>
        ${dayAvg!==null ? `<div class="mt-2">Siang: <strong>${dayAvg}°</strong></div>` : ``}
        ${nightAvg!==null ? `<div>Malam: <strong>${nightAvg}°</strong></div>` : ``}
      </div>
    </div>
    <div class="col-12 col-md-8">
      <div class="border rounded p-3 h-100">
        <div class="mb-2 fw-semibold">Detail</div>
        <ul class="mb-0">
          <li>Kode cuaca: ${d.wcode}</li>
          <li>Kota: ${escapeHtml(selectedCity.name)}</li>
          <li>Zona waktu: ${escapeHtml(forecast.timezone)}</li>
        </ul>
      </div>
    </div>
  `;
}

// Event listener untuk tombol hari (hari ini, besok, lusa)
document.querySelectorAll('[data-day]').forEach(btn => {
  btn.addEventListener('click', () => {
    setActiveDay(btn);
    renderForecastDay(parseInt(btn.getAttribute('data-day'), 10));
  });
});

/* --- QUIZ --- */
// Elemen-elemen terkait quiz
const qText     = document.getElementById('quiz-question');
const qOpts     = document.getElementById('quiz-options');
const qFeedback = document.getElementById('quiz-feedback');
const btnSubmit = document.getElementById('btn-submit-answer');
const btnNext   = document.getElementById('btn-next-question');
const myScore   = document.getElementById('my-score');

// Opsi topik yang terpilih
const topicSelect = document.getElementById('topic-select');

// Memastikan topik terpilih valid
function currentTopicId() {
  if (!topicSelect) return null;

  // Ambil dari nilai yang terpilih
  const v = topicSelect.value;
  let id = v ? parseInt(v, 10) : NaN;
  if (Number.isFinite(id)) return id;

  // Jika tidak ada yang terpilih, ambil dari opsi pertama
  if (topicSelect.options && topicSelect.options.length > 0) {
    id = parseInt(topicSelect.options[0].value, 10);
    if (Number.isFinite(id)) {
      // Set opsi terpilih ke yang pertama
      topicSelect.selectedIndex = 0;
      return id;
    }
  }
  return null;
}

// Inisialisasi topik terpilih saat pertama kali load
if (topicSelect) {
  topicSelect.addEventListener('change', (e) => {
    selectedTopicId = parseInt(e.target.value, 10);
    loadQuestion();
  });
}

// Soal saat ini
let currentQuestion = null;

// Ambil soal berikutnya dari API
async function loadQuestion() {
  if (!qText || !qOpts) return;

  const topicId = currentTopicId();  
  if (!Number.isFinite(topicId)) {
    qText.textContent = 'Topik tidak tersedia.';
    qOpts.innerHTML = '';
    return;
  }

  qFeedback.innerHTML = '';
  if (btnSubmit) btnSubmit.disabled = false;
  if (btnNext) btnNext.classList.add('d-none');
  qText.textContent = 'Memuat soal…';
  qOpts.innerHTML = '';

  const url = `/api/quiz/next?topic_id=${encodeURIComponent(topicId)}`;
  const r = await fetch(url);
  if (!r.ok) { qText.textContent = 'Gagal memuat soal.'; return; }
  const j = await r.json();
  currentQuestion = j;

  qText.textContent = j.question;
  qOpts.innerHTML = '';
  (j.options || []).forEach((opt, idx) => {
    const id = `opt-${idx}`;
    const wrap = document.createElement('div');
    wrap.className = 'form-check';
    wrap.innerHTML = `
      <input class="form-check-input" type="radio" name="answer" id="${id}" value="${idx}">
      <label class="form-check-label" for="${id}">${escapeHtml(opt)}</label>
    `;
    qOpts.appendChild(wrap);
  });
}

// Event listener untuk tombol submit jawaban
if (btnSubmit) {
  btnSubmit.addEventListener('click', async () => {
    if (!currentQuestion) return;
    const chosen = (document.querySelector('input[name="answer"]:checked') || {}).value;
    if (chosen === undefined) {
      qFeedback.innerHTML = `<div class="alert alert-warning">Pilih salah satu jawaban.</div>`;
      return;
    }
    btnSubmit.disabled = true;

    const r = await fetch('/api/quiz/answer', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken(),
      },
      body: JSON.stringify({ question_id: currentQuestion.question_id, chosen_index: parseInt(chosen, 10) })
    });
    const j = await r.json();
    if (j.error) {
      qFeedback.innerHTML = `<div class="alert alert-danger">${j.error}</div>`;
      return;
    }
    if (j.correct) {
      qFeedback.innerHTML = `<div class="alert alert-success">Jawaban benar! 🎉</div>`;
    } else {
      const label = document.querySelector(`#opt-${j.correct_index} + label`);
      qFeedback.innerHTML = `<div class="alert alert-danger">Kurang tepat. Jawaban benar: <strong>${label ? label.textContent : j.correct_index}</strong>.</div>`;
    }
    if (typeof j.new_score === 'number') {
      myScore && (myScore.textContent = j.new_score);
    }
    if (j.correct) fetchLeaderboard();
    btnNext && btnNext.classList.remove('d-none');
  });
}

// Event listener untuk tombol soal berikutnya
if (btnNext) {
  btnNext.addEventListener('click', () => {
    loadQuestion();
  });
}

// Inisialisasi saat pertama kali load
(() => {
  console.log('dashboard.js loaded');
  loadForecast();
  fetchLeaderboard();
  loadQuestion();   // muat soal pertama
})();