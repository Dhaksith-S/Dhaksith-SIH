/**
 * MINE-X DRONE COMMAND - Main Dashboard Orchestrator
 * Connects WebSocket client, coordinates 3D scene, controls, telemetry,
 * sensors, radar, modals (Hardware Inspector, Calibration, Mission Control), and layer toggles.
 */

class WebSocketClient {
  constructor(url, onMessageCallback, onStatusCallback) {
    this.url = url;
    this.onMessage = onMessageCallback;
    this.onStatus = onStatusCallback;
    this.ws = null;
    this.reconnectTimer = null;
    this.connect();
  }

  connect() {
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log("[WebSocket] Connected to MINE-X Drone Command server");
        if (this.onStatus) this.onStatus(true);
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (this.onMessage) this.onMessage(data);
        } catch (e) {
          console.error("[WebSocket] Parse error:", e);
        }
      };

      this.ws.onclose = () => {
        console.warn("[WebSocket] Disconnected. Reconnecting in 2s...");
        if (this.onStatus) this.onStatus(false);
        this.scheduleReconnect();
      };

      this.ws.onerror = (err) => {
        console.error("[WebSocket] Error:", err);
        if (this.onStatus) this.onStatus(false);
        this.ws.close();
      };
    } catch (e) {
      console.error("[WebSocket] Connection attempt failed:", e);
      this.scheduleReconnect();
    }
  }

  scheduleReconnect() {
    if (!this.reconnectTimer) {
      this.reconnectTimer = setTimeout(() => {
        this.reconnectTimer = null;
        this.connect();
      }, 2000);
    }
  }

  sendCommand(command, params = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const payload = { command, ...params };
      this.ws.send(JSON.stringify(payload));
    } else {
      console.warn("[WebSocket] Not connected. Command queued/dropped:", command);
    }
  }
}

class DashboardApp {
  constructor() {
    this.socket = null;
    this.drone3d = null;
    this.controls = null;
    this.telemetryUI = null;
    this.sensorsUI = null;
    this.radar = null;

    this.latestTelemetry = null;
    this.init();
  }

  init() {
    console.log("Initializing MINE-X DRONE COMMAND Dashboard...");

    // 1. Initialize 3D Engine
    this.drone3d = new Drone3DEngine('viewport-container');

    // 2. Initialize Telemetry UI & Sensors
    this.telemetryUI = new TelemetryUI();
    this.radar = new CavernRadar('radar-canvas');

    // 3. Initialize WebSocket
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host || 'localhost:8000';
    const wsUrl = `${wsProto}//${wsHost}/ws`;

    this.socket = new WebSocketClient(
      wsUrl,
      (data) => this.onTelemetryMessage(data),
      (isConnected) => this.onConnectionStatus(isConnected)
    );

    // 4. Initialize Controls & Sensors UI
    this.controls = new DroneControls(this.socket, this.drone3d);
    this.sensorsUI = new SensorsUI(this.socket);

    // 5. Setup Modals & Additional Controls
    this.setupModals();
    this.setupLayerToggles();
    this.setupMissionControl();
    this.setupStationSectorButtons();

    this.showToast("MINE-X Drone Command Online • SIMULATION MODE Active");
  }

  onConnectionStatus(connected) {
    const pill = document.getElementById('hud-conn-pill');
    if (pill) {
      if (connected) {
        pill.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping mr-1.5"></span> ONLINE`;
        pill.className = "flex items-center text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-700 mono-font";
      } else {
        pill.innerHTML = `<span class="w-2 h-2 rounded-full bg-red-500 mr-1.5"></span> RECONNECTING`;
        pill.className = "flex items-center text-[10px] font-bold px-2 py-0.5 rounded bg-red-950/80 text-red-400 border border-red-700 mono-font";
      }
    }
  }

  onTelemetryMessage(data) {
    if (!data) return;

    // Handle command acknowledgment
    if (data.type === 'COMMAND_ACK') {
      if (this.controls) this.controls.handleCommandAck(data.result);
      return;
    }

    this.latestTelemetry = data;

    // Update 3D drone position & motors
    this.drone3d.updateTelemetry(data);

    // Update telemetry gauges, cards, charts, fault banner
    this.telemetryUI.update(data);

    // Update arm-state button enabled/disabled states
    if (this.controls) {
      const isArmed = data.armed !== undefined ? data.armed : (data.flight_status?.armed || false);
      this.controls.updateArmStateUI(isArmed);
    }

    // Update sensors cards, atmospheric panel, alerts
    this.sensorsUI.update(data);

    // Update geospatial radar
    if (data.position) {
      this.radar.update(data.position, data.heading || 0);
    }

    // Update mission stats if running
    this.updateMissionDisplay(data);
  }

  setupModals() {
    // 1. Hardware Inspector Modal
    const btnHw = document.getElementById('btn-open-hardware');
    const modalHw = document.getElementById('modal-hardware-inspector');
    const closeHw = document.getElementById('btn-close-hardware');

    if (btnHw && modalHw) {
      btnHw.addEventListener('click', () => {
        this.populateHardwareInspector();
        modalHw.classList.remove('hidden');
      });
    }
    if (closeHw && modalHw) {
      closeHw.addEventListener('click', () => {
        modalHw.classList.add('hidden');
      });
    }

    // 2. Sensor Calibration Modal
    const btnCal = document.getElementById('btn-open-calibration');
    const modalCal = document.getElementById('modal-calibration');
    const closeCal = document.getElementById('btn-close-calibration');

    if (btnCal && modalCal) {
      btnCal.addEventListener('click', () => {
        modalCal.classList.remove('hidden');
      });
    }
    if (closeCal && modalCal) {
      closeCal.addEventListener('click', () => {
        modalCal.classList.add('hidden');
      });
    }

    // Attach calibration triggers
    ['imu', 'lidar', 'barometer', 'gas', 'camera'].forEach(sensor => {
      const btn = document.getElementById(`btn-cal-${sensor}`);
      if (btn) {
        btn.addEventListener('click', () => {
          this.executeSensorCalibration(sensor, btn);
        });
      }
    });

    // 3. Design Reference Video Modal
    const btnDesignRef = document.getElementById('btn-open-design-ref');
    const modalDesignRef = document.getElementById('modal-design-reference');
    const closeDesignRef = document.getElementById('btn-close-design-ref');
    const videoDesignRef = document.getElementById('design-ref-video');

    if (btnDesignRef && modalDesignRef) {
      btnDesignRef.addEventListener('click', () => {
        modalDesignRef.classList.remove('hidden');
        if (videoDesignRef) {
          videoDesignRef.currentTime = 0;
          videoDesignRef.play().catch(e => console.log('Autoplay muted blocked:', e));
        }
      });
    }
    if (closeDesignRef && modalDesignRef) {
      closeDesignRef.addEventListener('click', () => {
        modalDesignRef.classList.add('hidden');
        if (videoDesignRef) {
          videoDesignRef.pause();
        }
      });
    }

    // 4. Export CSV Button
    const btnExport = document.getElementById('btn-export-telemetry');
    if (btnExport) {
      btnExport.addEventListener('click', () => {
        window.location.href = '/api/export/csv';
        this.showToast("Telemetry CSV Export generated and downloading...");
      });
    }
  }

  executeSensorCalibration(sensor, btnElement) {
    const origText = btnElement.textContent;
    btnElement.textContent = "CALIBRATING...";
    btnElement.disabled = true;
    btnElement.className = "py-1.5 px-3 rounded bg-amber-600 text-white font-bold text-xs animate-pulse";

    this.socket.sendCommand('CALIBRATE', { sensor });

    setTimeout(() => {
      btnElement.textContent = "CALIBRATED ✓";
      btnElement.className = "py-1.5 px-3 rounded bg-emerald-600 text-white font-bold text-xs";
      this.showToast(`Sensor Calibration Complete: ${sensor.toUpperCase()}`);
      setTimeout(() => {
        btnElement.textContent = origText;
        btnElement.disabled = false;
        btnElement.className = "py-1.5 px-3 rounded bg-zinc-800 hover:bg-zinc-700 text-amber-400 font-bold text-xs border border-zinc-700";
      }, 2500);
    }, 2000);
  }

  populateHardwareInspector() {
    if (!this.latestTelemetry) return;
    const t = this.latestTelemetry;
    const s = t.sensors || {};

    const motors = s.motors || [];
    const escs = s.escs || [];
    const comp = s.onboard_computer || {};
    const pdb = s.power_rails || {};
    const batt = t.battery || {};

    let html = `
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs mono-font">
        <!-- Airframe & Physical Hardware -->
        <div class="p-3 rounded bg-zinc-900/90 border border-zinc-800 flex flex-col gap-1.5">
          <span class="text-amber-400 font-bold text-[11px] pb-1 border-b border-zinc-800 flex items-center justify-between">
            <span>AIRFRAME & DRIVETRAIN</span>
            <span class="text-emerald-400 font-bold">NORMAL</span>
          </span>
          <div class="flex justify-between"><span class="text-zinc-400">FRAME:</span><span>Carbon Fiber X-Frame</span></div>
          <div class="flex justify-between"><span class="text-zinc-400">PROTECTIVE CAGE:</span><span class="text-emerald-400">Rolling Cage (Active)</span></div>
          <div class="flex justify-between"><span class="text-zinc-400">WEIGHT:</span><span>2.85 kg AUW</span></div>
          <div class="flex justify-between"><span class="text-zinc-400">FLIGHT CONTROLLER:</span><span>PX4 FMUv6X (Simulated)</span></div>
          <div class="flex justify-between"><span class="text-zinc-400">MCU COPROCESSOR:</span><span>STM32H7 / ESP32-S3</span></div>
        </div>

        <!-- Onboard Companion Computer -->
        <div class="p-3 rounded bg-zinc-900/90 border border-zinc-800 flex flex-col gap-1.5">
          <span class="text-cyan-400 font-bold text-[11px] pb-1 border-b border-zinc-800 flex items-center justify-between">
            <span>ONBOARD COMPUTER</span>
            <span class="text-emerald-400 font-bold">ONLINE</span>
          </span>
          <div class="flex justify-between"><span class="text-zinc-400">MODEL:</span><span>${comp.model || 'Nvidia Jetson Orin NX 16GB'}</span></div>
          <div class="flex justify-between"><span class="text-zinc-400">CPU LOAD:</span><span>${comp.cpu_pct || 42}%</span></div>
          <div class="flex justify-between"><span class="text-zinc-400">GPU LOAD:</span><span>${comp.gpu_pct || 38}%</span></div>
          <div class="flex justify-between"><span class="text-zinc-400">RAM USAGE:</span><span>${comp.ram_pct || 60}%</span></div>
          <div class="flex justify-between"><span class="text-zinc-400">SOC TEMP:</span><span>${comp.temp_c || 52}°C</span></div>
          <div class="flex justify-between"><span class="text-zinc-400">STORAGE (SSD):</span><span>54% (276 GB Free)</span></div>
        </div>

        <!-- Power Distribution Board (PDB) & Battery -->
        <div class="p-3 rounded bg-zinc-900/90 border border-zinc-800 flex flex-col gap-1.5">
          <span class="text-amber-400 font-bold text-[11px] pb-1 border-b border-zinc-800 flex items-center justify-between">
            <span>POWER SYSTEM & BMS</span>
            <span class="text-emerald-400 font-bold">${batt.bms_status || 'NORMAL'}</span>
          </span>
          <div class="flex justify-between"><span class="text-zinc-400">BATTERY:</span><span class="text-amber-300 font-bold">${batt.percentage || 85}% (6S LiPo)</span></div>
          <div class="flex justify-between"><span class="text-zinc-400">MAIN BUS:</span><span>${(batt.voltage || 22.8).toFixed(1)}V @ ${(batt.current || 8.4).toFixed(1)}A</span></div>
          <div class="flex justify-between"><span class="text-zinc-400">5V REGULATOR:</span><span>${pdb.rail_5v || 5.02}V (Normal)</span></div>
          <div class="flex justify-between"><span class="text-zinc-400">12V REGULATOR:</span><span>${pdb.rail_12v || 12.04}V (Normal)</span></div>
          <div class="flex justify-between"><span class="text-zinc-400">24V BUS:</span><span>${pdb.rail_24v || 23.8}V</span></div>
          <div class="flex justify-between"><span class="text-zinc-400">PDB TEMP:</span><span>${pdb.pdb_temp_c || 34}°C</span></div>
        </div>
      </div>

      <!-- Motors & ESCs 4-Channel Matrix -->
      <div class="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs mono-font">
        ${motors.map((m, i) => `
          <div class="p-2.5 rounded bg-zinc-950 border border-zinc-800 flex flex-col gap-1">
            <span class="text-amber-400 font-bold flex justify-between">
              <span>MOTOR #${m.id}</span>
              <span class="text-[10px] ${m.temp_c > 70 ? 'text-red-400' : 'text-emerald-400'}">${m.status || 'OK'}</span>
            </span>
            <div class="flex justify-between"><span class="text-zinc-400">RPM:</span><span class="text-white font-bold">${m.rpm}</span></div>
            <div class="flex justify-between"><span class="text-zinc-400">CURRENT:</span><span>${m.current} A</span></div>
            <div class="flex justify-between"><span class="text-zinc-400">TEMP:</span><span>${m.temp_c}°C</span></div>
            <div class="flex justify-between"><span class="text-zinc-400">ESC #${m.id}:</span><span>${escs[i]?.temp_c || 40}°C (OK)</span></div>
          </div>
        `).join('')}
      </div>
    `;

    const container = document.getElementById('hardware-inspector-content');
    if (container) {
      container.innerHTML = html;
    }
  }

  setupLayerToggles() {
    const toggles = [
      { id: 'layer-rock', obj: () => this.drone3d.rockMesh },
      { id: 'layer-lidar', obj: () => this.drone3d.pointCloudMesh },
      { id: 'layer-corridor', obj: () => this.drone3d.corridorGroup },
      { id: 'layer-timbers', obj: () => this.drone3d.timberGroup },
      { id: 'layer-rails', obj: () => this.drone3d.railGroup },
      { id: 'layer-beacons', obj: () => this.drone3d.markerGroup },
      { id: 'layer-grid', obj: () => this.drone3d.gridGroup },
      { id: 'layer-gas-plume', obj: () => this.drone3d.gasPlumeGroup }
    ];

    toggles.forEach(t => {
      const el = document.getElementById(t.id);
      if (el) {
        el.addEventListener('change', (e) => {
          const mesh = t.obj();
          if (mesh) {
            mesh.visible = e.target.checked;
          }
        });
      }
    });

    // Geological Shaders
    const btnXray = document.getElementById('shader-xray');
    const btnTruecolor = document.getElementById('shader-truecolor');
    if (btnXray && btnTruecolor) {
      btnXray.addEventListener('click', () => {
        if (this.drone3d.wireframeMesh && this.drone3d.rockMesh) {
          this.drone3d.wireframeMesh.visible = true;
          this.drone3d.rockMesh.visible = false;
          btnXray.className = "px-2 py-1.5 rounded bg-amber-600 text-white font-semibold flex items-center gap-1.5 justify-center text-[10px]";
          btnTruecolor.className = "px-2 py-1.5 rounded bg-zinc-800 text-zinc-300 hover:bg-zinc-700 font-semibold flex items-center gap-1.5 justify-center text-[10px]";
          this.showToast("Shader: Sub-Surface X-Ray Wireframe Activated");
        }
      });

      btnTruecolor.addEventListener('click', () => {
        if (this.drone3d.wireframeMesh && this.drone3d.rockMesh) {
          this.drone3d.wireframeMesh.visible = false;
          this.drone3d.rockMesh.visible = true;
          btnTruecolor.className = "px-2 py-1.5 rounded bg-amber-600 text-white font-semibold flex items-center gap-1.5 justify-center text-[10px]";
          btnXray.className = "px-2 py-1.5 rounded bg-zinc-800 text-zinc-300 hover:bg-zinc-700 font-semibold flex items-center gap-1.5 justify-center text-[10px]";
          this.showToast("Shader: True Color Terracotta Ore Restored");
        }
      });
    }

    // Toggle Survey Floodlights
    const btnLights = document.getElementById('btn-toggle-lights');
    let lightsOn = true;
    if (btnLights) {
      btnLights.addEventListener('click', () => {
        lightsOn = !lightsOn;
        this.drone3d.surveySpotlights.forEach(s => s.visible = lightsOn);
        btnLights.textContent = lightsOn ? "FLOODLIGHTS ON" : "DIMMED";
        btnLights.className = lightsOn ?
          "px-2 py-0.5 rounded bg-amber-500 text-zinc-950 font-bold text-[10px]" :
          "px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 font-bold text-[10px]";
      });
    }
  }

  setupMissionControl() {
    const btnStart = document.getElementById('btn-mission-start');
    const btnPause = document.getElementById('btn-mission-pause');
    const btnAbort = document.getElementById('btn-mission-abort');

    if (btnStart) {
      btnStart.addEventListener('click', () => {
        this.socket.sendCommand('START_MISSION');
        this.showToast("Mission #001 Started: Autonomous Subterranean Inspection");
      });
    }
    if (btnPause) {
      btnPause.addEventListener('click', () => {
        this.socket.sendCommand('PAUSE_MISSION');
        this.showToast("Mission Paused");
      });
    }
    if (btnAbort) {
      btnAbort.addEventListener('click', () => {
        this.socket.sendCommand('ABORT_MISSION');
        this.showToast("Mission Aborted. Switching to Manual.");
      });
    }
  }

  updateMissionDisplay(data) {
    const dist = data.flight_status?.total_distance_m || 0;
    const durSec = data.flight_status?.flight_time_s || 0;
    const mins = Math.floor(durSec / 60);
    const secs = durSec % 60;

    const elDist = document.getElementById('mission-distance');
    const elTime = document.getElementById('mission-time');
    const elScanned = document.getElementById('mission-area-scanned');

    if (elDist) elDist.textContent = `${dist.toFixed(1)} m`;
    if (elTime) elTime.textContent = `${mins < 10 ? '0' : ''}${mins}:${secs < 10 ? '0' : ''}${secs}`;
    if (elScanned) {
      const pct = Math.min(100, Math.round((dist / 220) * 100));
      elScanned.textContent = `${pct}%`;
    }
  }

  setupStationSectorButtons() {
    const sectorCoords = [
      { x: 0, y: 5, z: 25 },
      { x: 10, y: 6.5, z: -25 },
      { x: -14, y: 9.5, z: -72 },
      { x: 16, y: 8, z: -118 },
      { x: -5, y: 4.5, z: -160 }
    ];

    document.querySelectorAll('.sector-card').forEach((btn, idx) => {
      btn.addEventListener('click', () => {
        if (this.drone3d && this.drone3d.orbitControls) {
          const tgt = sectorCoords[idx];
          if (tgt) {
            this.drone3d.camera.position.set(tgt.x, tgt.y + 14, tgt.z + 32);
            this.drone3d.orbitControls.target.set(tgt.x, tgt.y, tgt.z);
            this.showToast(`Camera Navigated to Sector: ${btn.dataset.sectorName || idx + 1}`);
          }
        }
      });
    });
  }

  showToast(msg) {
    const t = document.getElementById('toast');
    const txt = document.getElementById('toast-text');
    if (t && txt) {
      txt.textContent = msg;
      t.style.opacity = '1';
      clearTimeout(t._timer);
      t._timer = setTimeout(() => {
        t.style.opacity = '0';
      }, 2600);
    }
  }
}

// Instantiate on window load
window.addEventListener('DOMContentLoaded', () => {
  window.droneApp = new DashboardApp();
});
