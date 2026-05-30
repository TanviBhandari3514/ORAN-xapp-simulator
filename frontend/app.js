/**
 * O-RAN xApp Simulator - Frontend Application
 * Handles WebSocket connection and UI interactions.
 */

// --- WebSocket Connection ---
let ws = null;
let logsPaused = false;
let activeLayerFilter = 'all';

function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        updateConnectionBadge(true);
        addLog('system', 'Connected to backend');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    ws.onclose = () => {
        updateConnectionBadge(false);
        addLog('system', 'Disconnected from backend. Reconnecting...');
        setTimeout(connect, 3000);
    };

    ws.onerror = () => {
        ws.close();
    };
}

function send(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    }
}

// --- Message Handler ---
function handleMessage(data) {
    switch (data.type) {
        case 'system':
            addLog('system', data.message);
            break;
        case 'status':
            updateSimState(data.simulation);
            break;
        case 'log':
            if (data.entries) {
                data.entries.forEach(entry => addLog(entry.source, entry.message, entry.layer));
            }
            break;
        case 'pong':
            break;
        default:
            console.log('Unknown message:', data);
    }
}

// --- UI Updates ---
function updateConnectionBadge(connected) {
    const badge = document.getElementById('connection-badge');
    badge.textContent = connected ? 'Connected' : 'Disconnected';
    badge.className = `badge ${connected ? 'connected' : 'disconnected'}`;
}

function updateSimState(state) {
    const stateEl = document.getElementById('sim-state');
    const dot = stateEl.previousElementSibling;
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');

    stateEl.textContent = state.charAt(0).toUpperCase() + state.slice(1);
    dot.className = `dot ${state}`;

    btnStart.disabled = (state === 'running' || state === 'starting');
    btnStop.disabled = (state === 'stopped' || state === 'stopping');
}

function addLog(source, message, layer) {
    if (logsPaused) return;
    if (activeLayerFilter !== 'all' && layer && layer !== activeLayerFilter) return;

    const logOutput = document.getElementById('log-output');
    const entry = document.createElement('div');
    entry.className = `log-entry ${source}`;
    if (layer) entry.dataset.layer = layer;

    const time = new Date().toLocaleTimeString('en-US', { hour12: false, fractionalSecondDigits: 3 });
    entry.innerHTML = `<span class="log-time">${time}</span> <span class="log-source">[${source}]</span> ${message}`;

    logOutput.appendChild(entry);

    // Keep buffer at 500 entries max in DOM
    while (logOutput.children.length > 500) {
        logOutput.removeChild(logOutput.firstChild);
    }

    // Auto-scroll to bottom
    logOutput.scrollTop = logOutput.scrollHeight;
}

// --- Event Listeners ---
document.addEventListener('DOMContentLoaded', () => {
    // Connect WebSocket
    connect();

    // Start button
    document.getElementById('btn-start').addEventListener('click', () => {
        send({ command: 'start_simulation' });
        updateSimState('starting');
    });

    // Stop button
    document.getElementById('btn-stop').addEventListener('click', () => {
        send({ command: 'stop_simulation' });
        updateSimState('stopping');
    });

    // Apply parameters
    document.getElementById('btn-apply-params').addEventListener('click', () => {
        const params = {
            enb_count: parseInt(document.getElementById('param-enb').value),
            gnb_count: parseInt(document.getElementById('param-gnb').value),
            ue_count: parseInt(document.getElementById('param-ue').value),
            tx_power_dbm: parseFloat(document.getElementById('param-txpower').value),
            carrier_freq_ghz: parseFloat(document.getElementById('param-freq').value),
            bandwidth_mhz: parseInt(document.getElementById('param-bw').value),
        };
        send({ command: 'apply_params', params });
        addLog('system', 'Parameters applied');
    });

    // Pause/Resume logs
    document.getElementById('btn-pause-logs').addEventListener('click', (e) => {
        logsPaused = !logsPaused;
        e.target.textContent = logsPaused ? 'Resume' : 'Pause';
    });

    // Layer filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            activeLayerFilter = e.target.dataset.layer;
        });
    });
});
