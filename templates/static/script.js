let chartInstance = null;

// ── Add Expense ───────────────────────────────────
async function addExpense() {
  const amount = document.getElementById('amount').value;
  const category = document.getElementById('category').value;
  const description = document.getElementById('desc').value;
  
  if (!amount || amount <= 0) { 
    alert('Please enter a valid amount!'); 
    return; 
  }

  const res = await fetch('/transactions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      amount: parseFloat(amount), 
      category: category, 
      description: description 
    })
  });

  const data = await res.json();
  if (data.success) {
    document.getElementById('amount').value = '';
    document.getElementById('desc').value = '';
    loadData();
  }
}

// ── Load Dashboard ────────────────────────────────
async function loadData() {
  try {
    const res = await fetch('/summary');
    const data = await res.json();
    const cats = data.categories || {};
    const total = data.total || 0;

    document.getElementById('total-spent').textContent = '₹' + total.toLocaleString();
    const entries = Object.entries(cats);
    const top = entries.sort((a, b) => b[1] - a[1])[0];
    document.getElementById('top-cat').textContent = top ? top[0] : '—';

    const txRes = await fetch('/transactions');
    const txData = await txRes.json();
    document.getElementById('tx-count').textContent = txData.length;

    updateChart(cats);
    renderTransactions(txData);
  } catch (e) {
    console.error('Load error:', e);
  }
}

// ── Chart ─────────────────────────────────────────
function updateChart(categories) {
  const canvas = document.getElementById('chart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (chartInstance) chartInstance.destroy();
  
  const labels = Object.keys(categories);
  const values = Object.values(categories);
  if (labels.length === 0) return;

  const colors = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#f97316'];
  chartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: colors.slice(0, labels.length),
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#94a3b8', font: { size: 12 } }
        }
      }
    }
  });
}

// ── Transactions ──────────────────────────────────
function renderTransactions(txData) {
  const list = document.getElementById('tx-list');
  if (!list) return;
  
  if (!txData.length) {
    list.innerHTML = '<p style="color:#64748b;font-size:13px;">No transactions yet.</p>';
    return;
  }

  list.innerHTML = [...txData].reverse().slice(0, 10).map(t => `
    <div class="tx-item">
      <div>
        <span class="tx-cat">${t.category}</span>
        <span style="margin-left:8px;font-size:12px;color:#94a3b8;">${t.description || ''}</span>
      </div>
      <div class="tx-amt">-₹${parseFloat(t.amount).toLocaleString()}</div>
    </div>
  `).join('');
}

// ── Chat ──────────────────────────────────────────
async function sendChat() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';

  const box = document.getElementById('chatbox');
  box.innerHTML += `<div class="msg user">${msg}</div>`;

  const typingId = 'typing' + Date.now();
  box.innerHTML += `<div class="msg bot" id="${typingId}">⏳ Thinking...</div>`;
  box.scrollTop = box.scrollHeight;

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });
    const data = await res.json();
    document.getElementById(typingId).remove();
    box.innerHTML += `<div class="msg bot">${data.reply}</div>`;
  } catch (err) {
    document.getElementById(typingId).remove();
    box.innerHTML += `<div class="msg bot">❌ Error connecting. Please try again.</div>`;
  }
  box.scrollTop = box.scrollHeight;
}

// ── NLU Analyze ──────────────────────────────────
async function analyzeText() {
  const text = document.getElementById('nlu-text').value.trim();
  if (!text) { 
    alert('Please type something to analyze!'); 
    return; 
  }

  const resultDiv = document.getElementById('nlu-result');
  resultDiv.style.display = 'block';
  resultDiv.innerHTML = '<p style="color:#94a3b8;">⏳ Analyzing with IBM NLU...</p>';

  try {
    const res = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text })
    });
    const data = await res.json();

    if (data.error) {
      resultDiv.innerHTML = `<p style="color:#f87171;">❌ ${data.error}</p>`;
      return;
    }

    const keywords = (data.keywords || [])
      .map(k => `<span class="nlu-tag">${k.text}</span>`)
      .join('');

    const sentiment = data.sentiment?.document?.label || 'neutral';
    const score = parseFloat(data.sentiment?.document?.score || 0).toFixed(2);
    const emoji = sentiment === 'positive' ? '😊' : sentiment === 'negative' ? '😟' : '😐';
    const color = sentiment === 'positive' ? '#10b981' : sentiment === 'negative' ? '#f87171' : '#94a3b8';

    resultDiv.innerHTML = `
      <div style="margin-bottom:10px;">
        <strong style="color:#7dd3fc;">🔑 Keywords:</strong><br/>
        <div style="margin-top:6px;">${keywords || '<span style="color:#64748b;">None found</span>'}</div>
      </div>
      <div>
        <strong style="color:#7dd3fc;">💬 Sentiment:</strong>
        ${emoji} <span style="color:${color};font-weight:600;">${sentiment}</span>
        <span style="color:#64748b;"> (score: ${score})</span>
      </div>
    `;
  } catch (err) {
    resultDiv.innerHTML = '<p style="color:#f87171;">❌ Could not connect to NLU. Check your credentials.</p>';
  }
}

// ── Start ─────────────────────────────────────────
window.onload = function() {
  loadData();

  // Enter key sends chat
  const chatInput = document.getElementById('chat-input');
  if (chatInput) {
    chatInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') sendChat();
    });
  }
};