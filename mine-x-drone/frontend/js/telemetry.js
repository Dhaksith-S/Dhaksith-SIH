/**
 * MINE-X DRONE COMMAND - Telemetry UI Manager & Real-Time Single-Metric Trend Chart
 * Renders flight coordinates, kinematics, artificial horizon attitude gauge,
 * compact bottom metric cards, fault banner, and dedicated single-metric Chart.js graphs.
 */

class TelemetryUI {
  constructor() {
    this.chart = null;
    this.activeMetric = 'altitude'; // 'altitude' | 'battery' | 'velocity' | 'methane'
    this.chartHistoryDuration = 60; // default 60s
    this.chartDataBuffer = [];

    this.metricConfigs = {
      altitude: {
        label: 'ALTITUDE (m)',
        icon: 'fa-mountain',
        color: '#38bdf8',
        bgColor: 'rgba(56, 189, 248, 0.1)',
        min: 0,
        suggestedMax: 5.0,
        getValue: (d) => d.alt
      },
      battery: {
        label: 'BATTERY (%)',
        icon: 'fa-bolt',
        color: '#10b981',
        bgColor: 'rgba(16, 185, 129, 0.1)',
        min: 0,
        suggestedMax: 100.0,
        getValue: (d) => d.batt
      },
      velocity: {
        label: 'VELOCITY (m/s)',
        icon: 'fa-gauge-high',
        color: '#f59e0b',
        bgColor: 'rgba(245, 158, 11, 0.1)',
        min: 0,
        suggestedMax: 5.0,
        getValue: (d) => d.spd
      },
      methane: {
        label: 'METHANE (CH₄ %)',
        icon: 'fa-circle-nodes',
        color: '#34d399',
        bgColor: 'rgba(52, 211, 153, 0.1)',
        min: 0,
        suggestedMax: 0.1,
        getValue: (d) => d.ch4
      }
    };

    this.initChart();
    this.setupMetricCardListeners();
  }

  initChart() {
    const canvas = document.getElementById('telemetry-chart-canvas');
    if (!canvas || !window.Chart) return;

    const ctx = canvas.getContext('2d');
    const cfg = this.metricConfigs[this.activeMetric];

    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: cfg.label,
            borderColor: cfg.color,
            backgroundColor: cfg.bgColor,
            data: [],
            borderWidth: 1.8,
            pointRadius: 0,
            pointHoverRadius: 3,
            fill: true,
            tension: 0.25
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: {
          x: {
            display: true,
            grid: { color: 'rgba(255, 255, 255, 0.04)' },
            ticks: {
              color: '#64748b',
              font: { family: 'Share Tech Mono', size: 9 },
              maxTicksLimit: 6
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            min: cfg.min,
            suggestedMax: cfg.suggestedMax,
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: {
              color: '#94a3b8',
              font: { family: 'Share Tech Mono', size: 9 }
            }
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(10, 15, 24, 0.95)',
            titleFont: { family: 'Share Tech Mono', size: 10 },
            bodyFont: { family: 'Share Tech Mono', size: 11 },
            borderColor: cfg.color,
            borderWidth: 1
          }
        }
      }
    });

    // Setup Timescale Buttons
    [10, 30, 60, 300].forEach(sec => {
      const btn = document.getElementById(`btn-timescale-${sec}`);
      if (btn) {
        btn.addEventListener('click', () => {
          this.chartHistoryDuration = sec;
          [10, 30, 60, 300].forEach(s => {
            const b = document.getElementById(`btn-timescale-${s}`);
            if (b) {
              if (s === sec) {
                b.classList.add('active');
              } else {
                b.classList.remove('active');
              }
            }
          });
        });
      }
    });
  }

  setupMetricCardListeners() {
    ['altitude', 'battery', 'velocity', 'methane'].forEach(metric => {
      const card = document.getElementById(`card-metric-${metric}`);
      if (card) {
        card.addEventListener('click', () => {
          this.selectMetric(metric);
        });
      }
    });
  }

  selectMetric(metric) {
    if (!this.metricConfigs[metric]) return;
    this.activeMetric = metric;

    // Update selected card classes
    ['altitude', 'battery', 'velocity', 'methane'].forEach(m => {
      const c = document.getElementById(`card-metric-${m}`);
      if (c) {
        if (m === metric) {
          c.classList.add('selected');
        } else {
          c.classList.remove('selected');
        }
      }
    });

    // Update Chart header
    const cfg = this.metricConfigs[metric];
    const titleEl = document.getElementById('chart-metric-label');
    const iconEl = document.getElementById('chart-metric-icon');
    if (titleEl) {
      titleEl.textContent = cfg.label;
      titleEl.style.color = cfg.color;
    }
    if (iconEl) {
      iconEl.className = `fa-solid ${cfg.icon}`;
      iconEl.style.color = cfg.color;
    }

    // Reconfigure chart dataset & Y axis scale
    if (this.chart) {
      this.chart.data.datasets[0].label = cfg.label;
      this.chart.data.datasets[0].borderColor = cfg.color;
      this.chart.data.datasets[0].backgroundColor = cfg.bgColor;
      this.chart.options.scales.y.min = cfg.min;
      this.chart.options.scales.y.suggestedMax = cfg.suggestedMax;

      this.rebuildChartData();
    }
  }

  update(data) {
    if (!data) return;

    // 1. Top Header Telemetry & Status
    this.setText('coord-x', `${(data.position?.x || 0).toFixed(1)} m`);
    this.setText('coord-y', `${(data.position?.y || 0).toFixed(1)} m`);
    this.setText('coord-z', `${(data.position?.z || 0).toFixed(1)} m`);

    // Source Pill
    const sourcePill = document.getElementById('hud-source-pill');
    if (sourcePill) {
      const src = data.data_source || 'SIMULATION';
      sourcePill.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping"></span> ${src}`;
    }

    // Connection Pill
    const connPill = document.getElementById('hud-conn-pill');
    if (connPill && data.connection_status) {
      if (data.connection_status === 'ONLINE') {
        connPill.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping mr-1.5"></span> ONLINE`;
        connPill.className = "flex items-center text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-700/60";
      } else {
        connPill.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-red-400 mr-1.5"></span> OFFLINE`;
        connPill.className = "flex items-center text-[10px] font-bold px-2 py-0.5 rounded bg-red-950/80 text-red-300 border border-red-700/60";
      }
    }

    // Armed / Disarmed Pill
    const armedPill = document.getElementById('hud-armed-pill');
    const isArmed = data.armed !== undefined ? data.armed : (data.flight_status?.armed || false);

    if (armedPill) {
      if (isArmed) {
        armedPill.textContent = "ARMED";
        armedPill.className = "text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-950/90 text-emerald-300 border border-emerald-500 mono-font animate-pulse";
      } else {
        armedPill.textContent = "DISARMED";
        armedPill.className = "text-[10px] font-bold px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-700 mono-font";
      }
    }

    // Flight Mode Pill
    const mode = data.operating_mode || data.flight_status?.flight_mode || 'MANUAL';
    this.setText('hud-flight-mode', mode);
    const modePill = document.getElementById('hud-flight-mode');
    if (modePill) {
      if (mode === 'EMERGENCY') {
        modePill.className = "text-red-400 font-bold text-[11px] animate-pulse";
      } else {
        modePill.className = "text-cyan-400 font-bold text-[11px]";
      }
    }

    const modeSelect = document.getElementById('select-flight-mode');
    if (modeSelect && modeSelect !== document.activeElement) {
      modeSelect.value = mode;
    }

    // Active Fault Banner
    const fault = data.active_fault || (mode === 'EMERGENCY' ? {
      cause: "OPERATOR ENGAGED EMERGENCY KILL SWITCH",
      timestamp: data.time_str || "ACTIVE",
      recovery_status: "LATCHED - DISARM TO CLEAR"
    } : null);

    const faultBanner = document.getElementById('fault-banner');
    if (faultBanner) {
      if (fault) {
        faultBanner.classList.remove('hidden');
        this.setText('fault-cause', fault.cause || 'ACTIVE FAULT DETECTED');
        this.setText('fault-timestamp', fault.timestamp || data.time_str || '');
        this.setText('fault-recovery-status', fault.recovery_status || 'LATCHED');
      } else {
        faultBanner.classList.add('hidden');
      }
    }

    // Battery Quick & Card Readout
    const batt = data.battery || {};
    const battPct = batt.percentage !== undefined ? batt.percentage : 85.6;
    this.setText('batt-pct', `${battPct.toFixed(1)}%`);
    this.setText('card-batt-pct', `${battPct.toFixed(1)} %`);

    const battFill = document.getElementById('gauge-battery-fill');
    if (battFill) {
      battFill.style.width = `${Math.min(100, Math.max(0, battPct))}%`;
      battFill.style.backgroundColor = battPct < 20 ? '#ef4444' : (battPct < 40 ? '#f59e0b' : '#10b981');
    }

    // 2. Compact Bottom Metric Cards
    // Altitude Card
    const alt = data.altitude !== undefined ? data.altitude : (data.position?.y || 0);
    this.setText('telem-altitude', `${alt.toFixed(2)} m`);
    const altFill = document.getElementById('gauge-altitude-fill');
    if (altFill) {
      altFill.style.width = `${Math.min(100, Math.max(0, (alt / 5.0) * 100))}%`;
    }

    // Velocity Card
    const spd = data.ground_speed !== undefined ? data.ground_speed : (data.total_speed || 0);
    this.setText('telem-velocity', `${spd.toFixed(1)} m/s`);
    const velFill = document.getElementById('gauge-velocity-fill');
    if (velFill) {
      velFill.style.width = `${Math.min(100, Math.max(0, (spd / 5.0) * 100))}%`;
    }

    // Methane Card
    const ch4 = data.sensors?.gas?.ch4_pct || 0.028;
    this.setText('card-methane-val', `${ch4.toFixed(3)} %`);

    // 3. IMU Artificial Horizon Gauge
    const roll = data.orientation?.roll || 0;
    const pitch = data.orientation?.pitch || 0;
    const yaw = data.orientation?.yaw || 0;

    this.setText('hud-roll', `${(roll >= 0 ? '+' : '')}${roll.toFixed(1)}°`);
    this.setText('hud-pitch', `${(pitch >= 0 ? '+' : '')}${pitch.toFixed(1)}°`);
    this.setText('hud-yaw', `${yaw.toFixed(1)}°`);

    const horizonSky = document.getElementById('attitude-sky-ground');
    if (horizonSky) {
      horizonSky.style.transform = `rotate(${-roll}deg) translateY(${pitch * 1.3}px)`;
    }

    // 4. Update Rolling Chart Buffer & Chart View
    this.updateChartData(data);
  }

  updateChartData(data) {
    const now = Date.now();
    const timeLabel = new Date().toLocaleTimeString();

    this.chartDataBuffer.push({
      time: timeLabel,
      timestamp: now,
      alt: data.altitude !== undefined ? data.altitude : (data.position?.y || 0),
      batt: data.battery?.percentage !== undefined ? data.battery.percentage : 85.6,
      spd: data.ground_speed !== undefined ? data.ground_speed : 0,
      ch4: data.sensors?.gas?.ch4_pct !== undefined ? data.sensors.gas.ch4_pct : 0.028
    });

    const cutoff = now - (this.chartHistoryDuration * 1000);
    this.chartDataBuffer = this.chartDataBuffer.filter(d => d.timestamp >= cutoff);

    this.rebuildChartData();
  }

  rebuildChartData() {
    if (!this.chart || this.chartDataBuffer.length === 0) return;

    const cfg = this.metricConfigs[this.activeMetric];
    if (!cfg) return;

    // Subsample buffer for high framerate smoothness
    const maxPoints = 50;
    const step = Math.max(1, Math.floor(this.chartDataBuffer.length / maxPoints));
    const sampled = this.chartDataBuffer.filter((_, i) => i % step === 0);

    this.chart.data.labels = sampled.map(d => d.time);
    this.chart.data.datasets[0].data = sampled.map(d => cfg.getValue(d));

    this.chart.update('none');
  }

  setText(id, text) {
    const el = document.getElementById(id);
    if (el && el.textContent !== text) {
      el.textContent = text;
    }
  }
}
