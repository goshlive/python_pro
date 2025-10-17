// Memformat tanggal/waktu
function fmtDateTimeID(d = new Date()) {
  const opts = { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric',
                 hour: '2-digit', minute: '2-digit' };
  return new Intl.DateTimeFormat('id-ID', opts).format(d);
}

// Menampilkan informasi hari,tanggal,jam
const greetEl = document.getElementById('greet-datetime');
if (greetEl) greetEl.textContent = fmtDateTimeID();