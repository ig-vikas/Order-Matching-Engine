/**
 * Order Matching Engine — Web Trading Terminal JavaScript
 * Integrates REST API & WebSockets for real-time order matching visualization.
 */

let currentSymbol = 'AAPL';
let currentSide = 'BUY';
let currentOrderType = 'LIMIT';
let ws = null;
let priceHistory = [];

document.addEventListener('DOMContentLoaded', () => {
  initSymbols();
  initEventListeners();
  switchSymbol('AAPL');
});

// Initialize Symbol Selector
function initSymbols() {
  const symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'];
  const container = document.getElementById('symbol-selector');
  container.innerHTML = '';
  
  symbols.forEach(sym => {
    const btn = document.createElement('button');
    btn.className = `symbol-btn ${sym === currentSymbol ? 'active' : ''}`;
    btn.innerText = sym;
    btn.addEventListener('click', () => switchSymbol(sym));
    container.appendChild(btn);
  });
}

// Switch Active Symbol
function switchSymbol(symbol) {
  currentSymbol = symbol;
  
  // Update button active state
  document.querySelectorAll('.symbol-btn').forEach(btn => {
    btn.classList.toggle('active', btn.innerText === symbol);
  });
  
  document.getElementById('current-symbol-header').innerText = symbol;
  
  // Clear price history for chart
  priceHistory = [];
  
  // Fetch initial REST data
  fetchOrderBook();
  fetchTradeHistory();
  fetchAnalytics();
  
  // Connect WebSocket Feed
  connectWebSocket(symbol);
}

// Event Listeners for Order Entry Form
function initEventListeners() {
  // Side toggle (BUY / SELL)
  document.getElementById('btn-side-buy').addEventListener('click', () => setSide('BUY'));
  document.getElementById('btn-side-sell').addEventListener('click', () => setSide('SELL'));

  // Order Type Tabs (LIMIT, MARKET, IOC, FOK)
  document.querySelectorAll('.type-tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
      document.querySelectorAll('.type-tab').forEach(t => t.classList.remove('active'));
      e.target.classList.add('active');
      setOrderType(e.target.dataset.type);
    });
  });

  // Order Form Submit
  document.getElementById('order-form').addEventListener('submit', handleOrderSubmit);
}

function setSide(side) {
  currentSide = side;
  const buyBtn = document.getElementById('btn-side-buy');
  const sellBtn = document.getElementById('btn-side-sell');
  const submitBtn = document.getElementById('submit-btn');

  if (side === 'BUY') {
    buyBtn.classList.add('active');
    sellBtn.classList.remove('active');
    submitBtn.innerText = `Buy ${currentSymbol}`;
    submitBtn.style.background = 'linear-gradient(135deg, var(--accent-buy), #059669)';
  } else {
    sellBtn.classList.add('active');
    buyBtn.classList.remove('active');
    submitBtn.innerText = `Sell ${currentSymbol}`;
    submitBtn.style.background = 'linear-gradient(135deg, var(--accent-sell), #e11d48)';
  }
}

function setOrderType(type) {
  currentOrderType = type;
  const priceGroup = document.getElementById('price-group');
  const priceInput = document.getElementById('order-price');

  if (type === 'MARKET') {
    priceGroup.style.display = 'none';
    priceInput.removeAttribute('required');
  } else {
    priceGroup.style.display = 'flex';
    priceInput.setAttribute('required', 'true');
  }
}

// Handle Order Submission
async function handleOrderSubmit(e) {
  e.preventDefault();
  
  const quantityInput = document.getElementById('order-qty');
  const priceInput = document.getElementById('order-price');

  const quantity = parseInt(quantityInput.value);
  const price = currentOrderType === 'MARKET' ? null : parseFloat(priceInput.value);

  const payload = {
    symbol: currentSymbol,
    side: currentSide,
    order_type: currentOrderType,
    quantity: quantity
  };

  if (price !== null) {
    payload.price = price;
  }

  try {
    const response = await fetch('/api/v1/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (!response.ok) {
      const errDetail = data.detail ? (Array.isArray(data.detail) ? data.detail[0].msg : data.detail) : 'Submission failed';
      showToast(`Error: ${errDetail}`, 'error');
      return;
    }

    showToast(`Order #${data.order_id} (${data.status}) submitted!`, 'success');
    
    // Refresh data
    fetchOrderBook();
    fetchTradeHistory();
    fetchAnalytics();
  } catch (err) {
    showToast(`Network Error: ${err.message}`, 'error');
  }
}

// Fetch Order Book Depth (REST fallback + WS trigger)
async function fetchOrderBook() {
  try {
    const res = await fetch(`/api/v1/orderbook/${currentSymbol}?levels=8`);
    if (!res.ok) return;
    const data = await res.json();
    renderOrderBook(data);
  } catch (err) {
    console.error('Orderbook fetch failed:', err);
  }
}

// Render Order Book Ladder
function renderOrderBook(book) {
  const asksContainer = document.getElementById('ob-asks');
  const bidsContainer = document.getElementById('ob-bids');
  const spreadValue = document.getElementById('spread-value');

  // Update Spread
  if (book.best_bid && book.best_ask) {
    const spread = (book.best_ask - book.best_bid).toFixed(2);
    spreadValue.innerText = `$${spread}`;
  } else {
    spreadValue.innerText = '—';
  }

  // Calculate maximum volume for depth bars
  let maxVol = 1;
  const allVol = [...book.asks, ...book.bids].map(x => x.volume);
  if (allVol.length > 0) maxVol = Math.max(...allVol);

  // Render Asks (Reverse so highest ask is at top)
  asksContainer.innerHTML = '';
  const asksReversed = [...book.asks].reverse();
  asksReversed.forEach(ask => {
    const pct = Math.min(100, (ask.volume / maxVol) * 100);
    const row = document.createElement('div');
    row.className = 'ob-row ask';
    row.innerHTML = `
      <div class="bg-bar" style="width: ${pct}%"></div>
      <span class="price-ask">$${ask.price.toFixed(2)}</span>
      <span class="qty-col">${ask.volume}</span>
      <span class="total-col">${ask.order_count} ord</span>
    `;
    row.addEventListener('click', () => {
      document.getElementById('order-price').value = ask.price.toFixed(2);
    });
    asksContainer.appendChild(row);
  });

  // Render Bids
  bidsContainer.innerHTML = '';
  book.bids.forEach(bid => {
    const pct = Math.min(100, (bid.volume / maxVol) * 100);
    const row = document.createElement('div');
    row.className = 'ob-row bid';
    row.innerHTML = `
      <div class="bg-bar" style="width: ${pct}%"></div>
      <span class="price-bid">$${bid.price.toFixed(2)}</span>
      <span class="qty-col">${bid.volume}</span>
      <span class="total-col">${bid.order_count} ord</span>
    `;
    row.addEventListener('click', () => {
      document.getElementById('order-price').value = bid.price.toFixed(2);
    });
    bidsContainer.appendChild(row);
  });
}

// Fetch Trade History
async function fetchTradeHistory() {
  try {
    const res = await fetch(`/api/v1/trades/${currentSymbol}?limit=20`);
    if (!res.ok) return;
    const trades = await res.json();
    renderTradeHistory(trades);
  } catch (err) {
    console.error('Trades fetch failed:', err);
  }
}

// Render Trade History
function renderTradeHistory(trades) {
  const container = document.getElementById('trade-feed');
  container.innerHTML = '';

  trades.forEach(trade => {
    const timeStr = new Date(trade.timestamp).toLocaleTimeString();
    const row = document.createElement('div');
    row.className = 'trade-row';
    row.innerHTML = `
      <span style="color: var(--accent-cyan)">$${trade.price.toFixed(2)}</span>
      <span style="text-align: center">${trade.quantity}</span>
      <span style="text-align: right; color: var(--text-dim)">${timeStr}</span>
    `;
    container.appendChild(row);

    // Track price history for Canvas chart
    if (!priceHistory.some(p => p.id === trade.trade_id)) {
      priceHistory.push({ id: trade.trade_id, price: trade.price, time: timeStr });
    }
  });

  renderCanvasChart();
}

// Fetch Analytics Stats
async function fetchAnalytics() {
  try {
    const vwapRes = await fetch(`/api/v1/analytics/${currentSymbol}/vwap?hours=24`);
    if (vwapRes.ok) {
      const vwapData = await vwapRes.json();
      if (vwapData.length > 0) {
        document.getElementById('stat-vwap').innerText = `$${vwapData[0].vwap.toFixed(2)}`;
        document.getElementById('stat-volume').innerText = vwapData[0].total_volume;
      }
    }

    const spreadRes = await fetch(`/api/v1/analytics/${currentSymbol}/spread?limit=1`);
    if (spreadRes.ok) {
      const spreadData = await spreadRes.json();
      if (spreadData.length > 0) {
        document.getElementById('stat-price').innerText = `$${spreadData[0].price.toFixed(2)}`;
      }
    }
  } catch (err) {
    console.error('Analytics fetch error:', err);
  }
}

// Real-Time WebSocket Connection
function connectWebSocket(symbol) {
  if (ws) {
    ws.close();
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/feed/${symbol}`;

  ws = new WebSocket(wsUrl);

  const dot = document.getElementById('ws-status-dot');
  const label = document.getElementById('ws-status-text');

  ws.onopen = () => {
    dot.classList.add('online');
    label.innerText = 'LIVE FEED';
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.event === 'trade' || msg.event === 'book_update') {
      fetchOrderBook();
      fetchTradeHistory();
      fetchAnalytics();
    }
  };

  ws.onclose = () => {
    dot.classList.remove('online');
    label.innerText = 'DISCONNECTED';
  };

  ws.onerror = (err) => {
    console.error('WebSocket Error:', err);
  };
}

// Render HTML5 Canvas Live Line/Price Chart
function renderCanvasChart() {
  const canvas = document.getElementById('price-chart');
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  
  // Set dimensions based on wrapper size
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;

  ctx.clearRect(0, 0, w, h);

  if (priceHistory.length < 2) {
    ctx.fillStyle = '#64748b';
    ctx.font = '14px Outfit, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Waiting for trade data to populate chart...', w / 2, h / 2);
    return;
  }

  const prices = priceHistory.slice(-30).map(p => p.price);
  const minP = Math.min(...prices) * 0.995;
  const maxP = Math.max(...prices) * 1.005;

  const points = prices.map((price, idx) => {
    const x = (idx / (prices.length - 1)) * (w - 60) + 30;
    const y = h - 30 - ((price - minP) / (maxP - minP)) * (h - 60);
    return { x, y, price };
  });

  // Draw Grid Lines
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
  ctx.lineWidth = 1;
  for (let i = 1; i <= 4; i++) {
    const y = (h / 5) * i;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  // Draw Gradient Line
  const gradient = ctx.createLinearGradient(0, 0, w, 0);
  gradient.addColorStop(0, '#38bdf8');
  gradient.addColorStop(1, '#818cf8');

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i++) {
    ctx.lineTo(points[i].x, points[i].y);
  }
  ctx.strokeStyle = gradient;
  ctx.lineWidth = 3;
  ctx.stroke();

  // Draw Fill Area
  const fillGradient = ctx.createLinearGradient(0, 0, 0, h);
  fillGradient.addColorStop(0, 'rgba(56, 189, 248, 0.25)');
  fillGradient.addColorStop(1, 'rgba(56, 189, 248, 0.0)');

  ctx.lineTo(points[points.length - 1].x, h - 30);
  ctx.lineTo(points[0].x, h - 30);
  ctx.closePath();
  ctx.fillStyle = fillGradient;
  ctx.fill();

  // Draw Data Points
  points.forEach((pt, idx) => {
    ctx.beginPath();
    ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = idx === points.length - 1 ? '#10b981' : '#38bdf8';
    ctx.fill();
    ctx.strokeStyle = '#070a12';
    ctx.lineWidth = 2;
    ctx.stroke();
  });
}

// Toast Notification Helper
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerText = message;
  
  container.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Window Resize Chart Adjust
window.addEventListener('resize', renderCanvasChart);
