// Tauri v2 API
const invoke = window.__TAURI__?.core?.invoke || window.__TAURI__?.tauri?.invoke;
const listen = window.__TAURI__?.event?.listen;

// DOM elements
const wattsActual = document.getElementById('watts-actual');
const wattsMax = document.getElementById('watts-max');
const powerProgress = document.getElementById('power-progress');
const batteryPercent = document.getElementById('battery-percent');
const voltage = document.getElementById('voltage');
const amperage = document.getElementById('amperage');
const chargerName = document.getElementById('charger-name');
const statusIndicator = document.getElementById('status');
const lastUpdate = document.getElementById('last-update');

// Format number with fixed decimal places
function formatNumber(num, decimals = 1) {
  return Number(num).toFixed(decimals);
}

// Format timestamp
function formatTimestamp() {
  const now = new Date();
  return now.toLocaleTimeString('zh-TW', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}

// Update UI with power data
function updateUI(data) {
  console.log('🔄 Updating UI with data:', data);

  // Update watts display
  const watts = data.watts_actual;
  const isCharging = watts > 0;

  wattsActual.textContent = formatNumber(Math.abs(watts));
  wattsMax.textContent = data.watts_negotiated;

  // Update progress bar
  const percentage = Math.min((Math.abs(watts) / data.watts_negotiated) * 100, 100);
  powerProgress.style.width = `${percentage}%`;

  // Update charging/discharging state
  if (isCharging) {
    powerProgress.classList.remove('discharging');
    statusIndicator.classList.remove('discharging');
  } else {
    powerProgress.classList.add('discharging');
    statusIndicator.classList.add('discharging');
  }

  // Update battery info
  batteryPercent.textContent = `${data.battery_percent}%`;
  voltage.textContent = `${formatNumber(data.voltage, 2)} V`;
  amperage.textContent = `${formatNumber(data.amperage, 2)} A`;
  chargerName.textContent = data.charger_name || '未連接';

  // Update last update time
  lastUpdate.textContent = formatTimestamp();
}

// Initial data load
async function loadInitialData() {
  debugLog('Calling get_power_data...');
  try {
    const data = await invoke('get_power_data');
    debugLog('Got data: ' + JSON.stringify(data).substring(0, 100));
    updateUI(data);
  } catch (error) {
    debugLog('Load error: ' + error.message);
    console.error('Failed to load initial data:', error);
    // Show placeholder values
    wattsActual.textContent = '--';
    wattsMax.textContent = '--';
    batteryPercent.textContent = '--';
    voltage.textContent = '--';
    amperage.textContent = '--';
    chargerName.textContent = '載入中...';
  }
}

// Listen for power updates from backend
async function setupEventListener() {
  debugLog('Setting up event listener...');
  await listen('power-update', (event) => {
    debugLog('📥 Received power-update event');
    updateUI(event.payload);
  });
}

// Debug helper
function debugLog(msg) {
  console.log(msg);
  const debugEl = document.getElementById('debug');
  if (debugEl) {
    debugEl.innerHTML += msg + '<br>';
  }
}

// Initialize app
async function init() {
  debugLog('🚀 Initializing PowerFlow...');
  debugLog('invoke type: ' + typeof invoke);
  debugLog('listen type: ' + typeof listen);

  try {
    await setupEventListener();
    debugLog('✅ Event listener setup');

    await loadInitialData();
    debugLog('✅ Initial data loaded');
  } catch (error) {
    debugLog('❌ Init error: ' + error.message);
    console.error('Full error:', error);
  }
}

// Run when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
