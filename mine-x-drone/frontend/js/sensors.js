/**
 * MINE-X DRONE COMMAND - Sensors & Atmospheric Monitor UI
 * Renders the 5-gas atmospheric monitor, stale data detection (>3s),
 * 6-axis ToF obstacle rangefinders, and synthetic camera feed.
 */

class SensorsUI {
  constructor(socketClient) {
    this.socket = socketClient;
    this.lastGasUpdateTime = Date.now();
    this.staleThresholdMs = 3000; // 3 seconds stale threshold
    this.rgbCanvas = document.getElementById('camera-feed-canvas');

    // Run periodic stale check every 1s
    setInterval(() => this.checkStaleData(), 1000);
  }

  update(data) {
    if (!data || !data.sensors) return;
    const s = data.sensors;

    // 1. Dedicated Atmospheric Monitor (5 Gases)
    if (s.gas) {
      this.lastGasUpdateTime = Date.now();
      this.updateAtmosphericMonitor(s.gas, data.data_source || 'SIMULATION');
    }

    // 2. 6-Direction Obstacle Rangefinders (ToF)
    if (s.distances) {
      this.updateObstacleSensors(s.distances);
    }

    // 3. Render Synthetic Camera Feed
    this.renderSyntheticCameraFeed(data);

    // 4. Safety Alerts Summary
    if (data.alerts) {
      this.updateAlerts(data.alerts);
    }
  }

  updateAtmosphericMonitor(gas, dataSource) {
    const ch4 = gas.ch4_pct !== undefined ? gas.ch4_pct : 0.028;
    const co = gas.co_ppm !== undefined ? gas.co_ppm : 3.9;
    const co2 = gas.co2_ppm !== undefined ? gas.co2_ppm : 512;
    const o2 = gas.o2_pct !== undefined ? gas.o2_pct : 20.8;
    const h2s = gas.h2s_ppm !== undefined ? gas.h2s_ppm : 0.0;

    // Update gas value text
    this.setText('gas-ch4-val', `${ch4.toFixed(3)} %`);
    this.setText('gas-co-val', `${co.toFixed(1)} ppm`);
    this.setText('gas-co2-val', `${co2.toFixed(0)} ppm`);
    this.setText('gas-o2-val', `${o2.toFixed(1)} %`);
    this.setText('gas-h2s-val', `${h2s.toFixed(1)} ppm`);

    // Status evaluation for each gas
    const isCh4Warn = ch4 >= 0.50;
    const isCoWarn = co >= 25.0;
    const isCo2Warn = co2 >= 1000.0;
    const isO2Warn = o2 < 19.5;
    const isH2sWarn = h2s >= 10.0;

    this.updateGasPill('gas-ch4-pill', isCh4Warn ? 'WARNING' : 'NORMAL');
    this.updateGasPill('gas-co-pill', isCoWarn ? 'WARNING' : 'NORMAL');
    this.updateGasPill('gas-co2-pill', isCo2Warn ? 'WARNING' : 'NORMAL');
    this.updateGasPill('gas-o2-pill', isO2Warn ? 'WARNING' : 'NORMAL');
    this.updateGasPill('gas-h2s-pill', isH2sWarn ? 'WARNING' : 'NORMAL');

    // Overall Status
    const anyHazard = isCh4Warn || isCoWarn || isCo2Warn || isO2Warn || isH2sWarn;
    const statusEl = document.getElementById('gas-overall-status');
    if (statusEl) {
      if (anyHazard) {
        statusEl.textContent = "HAZARDOUS THRESHOLD EXCEEDED";
        statusEl.className = "px-2 py-0.5 rounded bg-red-950/90 text-red-400 border border-red-500 font-bold mono-font text-[9px] animate-pulse";
      } else {
        if (dataSource === 'SIMULATION') {
          statusEl.textContent = "READINGS WITHIN SIMULATED THRESHOLDS";
        } else {
          statusEl.textContent = "READINGS WITHIN CERTIFIED LIMITS";
        }
        statusEl.className = "px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/60 font-bold mono-font text-[9px]";
      }
    }
  }

  updateGasPill(id, status) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = status;
    if (status === 'WARNING' || status === 'CRITICAL') {
      el.className = "text-[9px] px-1.5 py-0.2 rounded bg-amber-950/90 text-amber-300 border border-amber-600 font-semibold animate-pulse";
    } else if (status === 'STALE') {
      el.className = "text-[9px] px-1.5 py-0.2 rounded bg-slate-900 text-slate-400 border border-slate-700 font-semibold";
    } else {
      el.className = "text-[9px] px-1.5 py-0.2 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800 font-semibold";
    }
  }

  checkStaleData() {
    const elapsed = Date.now() - this.lastGasUpdateTime;
    const statusEl = document.getElementById('gas-overall-status');

    if (elapsed > this.staleThresholdMs && statusEl) {
      statusEl.textContent = "STALE DATA — SENSOR DISCONNECTED";
      statusEl.className = "px-2 py-0.5 rounded bg-amber-950/90 text-amber-400 border border-amber-600 font-bold mono-font text-[9px] animate-pulse";
    }
  }

  updateObstacleSensors(dist) {
    const directions = ['front', 'rear', 'left', 'right', 'up', 'down'];
    directions.forEach(d => {
      const val = dist[d] !== undefined ? dist[d] : 9.9;
      const el = document.getElementById(`dist-${d}`);
      if (el) {
        el.textContent = `${val.toFixed(1)}m`;
        el.className = "dist-pill font-bold " + (val < 1.5 ? 'danger' : (val < 3.0 ? 'warn' : 'safe'));
      }
    });
  }

  renderSyntheticCameraFeed(data) {
    if (!this.rgbCanvas) return;
    const ctx = this.rgbCanvas.getContext('2d');
    const w = this.rgbCanvas.width;
    const h = this.rgbCanvas.height;

    // Subterranean mine tunnel background with searchlight cone
    ctx.fillStyle = '#0a0d14';
    ctx.fillRect(0, 0, w, h);

    // Cavern rock outline
    ctx.save();
    const grad = ctx.createRadialGradient(w / 2, h / 2 + 10, 10, w / 2, h / 2, w / 1.6);
    grad.addColorStop(0, 'rgba(255, 235, 200, 0.45)');
    grad.addColorStop(0.5, 'rgba(180, 120, 60, 0.15)');
    grad.addColorStop(1, 'rgba(0, 0, 0, 0.95)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);

    // Tunnel frame & timber crossbeam wireframes
    ctx.strokeStyle = 'rgba(217, 119, 6, 0.4)';
    ctx.lineWidth = 1.2;
    ctx.strokeRect(30, 20, w - 60, h - 35);

    // Floor track lines
    ctx.beginPath();
    ctx.moveTo(30, h - 15);
    ctx.lineTo(w / 2 - 10, h / 2 + 25);
    ctx.moveTo(w - 30, h - 15);
    ctx.lineTo(w / 2 + 10, h / 2 + 25);
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.4)';
    ctx.stroke();

    // Crosshair target
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.6)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(w / 2 - 12, h / 2);
    ctx.lineTo(w / 2 + 12, h / 2);
    ctx.moveTo(w / 2, h / 2 - 12);
    ctx.lineTo(w / 2, h / 2 + 12);
    ctx.stroke();

    // Timestamp & HUD text overlay
    ctx.fillStyle = '#38bdf8';
    ctx.font = '9px "Share Tech Mono"';
    ctx.fillText(`MINE-X CAM • 30FPS • ${(data.altitude || 0.35).toFixed(2)}m`, 8, 14);

    ctx.restore();
  }

  updateAlerts(alerts) {
    const list = document.getElementById('safety-alerts-list');
    const badge = document.getElementById('safety-alert-badge');
    if (!list || !badge) return;

    badge.textContent = `${alerts.length} ACTIVE`;
    badge.className = alerts.length > 0 ?
      "px-1.5 py-0.5 rounded bg-red-950 text-red-300 font-bold mono-font text-[9px] animate-pulse" :
      "px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-bold mono-font text-[9px]";

    if (alerts.length === 0) {
      list.innerHTML = `<div class="text-slate-500 py-1 text-center italic">All Safety Parameters Nominal</div>`;
      return;
    }

    list.innerHTML = alerts.map(a => `
      <div class="p-1 rounded bg-red-950/60 border border-red-800/80 flex items-center justify-between text-[9px] mono-font">
        <span class="text-red-300 truncate max-w-[190px]"><i class="fa-solid fa-triangle-exclamation mr-1"></i>${a.message || a.code}</span>
        <button class="px-1 bg-red-800 hover:bg-red-700 text-white rounded text-[8px]" onclick="(window.droneApp || window.dashboardApp).socket.sendCommand('ACK_ALERT', { alert_id: ${a.id} })">ACK</button>
      </div>
    `).join('');
  }

  setText(id, text) {
    const el = document.getElementById(id);
    if (el && el.textContent !== text) {
      el.textContent = text;
    }
  }
}
