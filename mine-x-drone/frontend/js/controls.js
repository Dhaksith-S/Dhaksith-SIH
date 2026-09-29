/**
 * MINE-X DRONE COMMAND - Control Handler
 * Manages operator keyboard controls, primary flight actions, collapsible accordions,
 * arm-state button enable/disable conditions, and command ACK feedback.
 */

class DroneControls {
  constructor(socketClient, drone3dEngine) {
    this.socket = socketClient;
    this.drone3d = drone3dEngine;

    this.keys = {
      w: false, s: false, a: false, d: false,
      q: false, e: false, r: false, f: false,
      space: false, shift: false, control: false
    };

    this.keyMap = {
      'KeyW': 'w', 'KeyS': 's', 'KeyA': 'a', 'KeyD': 'd',
      'KeyQ': 'q', 'KeyE': 'e', 'KeyR': 'r', 'KeyF': 'f',
      'ArrowUp': 'w', 'ArrowDown': 's', 'ArrowLeft': 'a', 'ArrowRight': 'd',
      'PageUp': 'r', 'PageDown': 'f',
      'KeyT': 'arm_toggle', 'KeyH': 'hover',
      'Space': 'space', 'ShiftLeft': 'shift', 'ShiftRight': 'shift',
      'ControlLeft': 'control', 'ControlRight': 'control'
    };

    this.commandTimeoutTimer = null;
    this.init();
  }

  init() {
    // 1. Keyboard event listeners (global window capture)
    window.addEventListener('keydown', (e) => this.handleKeyDown(e), true);
    window.addEventListener('keyup', (e) => this.handleKeyUp(e), true);

    // 2. Flight Action Buttons
    this.setupButtonListeners();

    // 3. Interactive On-Screen D-Pad / Keycaps (Click & Hold with Mouse or Touch)
    this.setupInteractiveKeycaps();

    // 4. Setup Accordions
    this.setupAccordions();

    // 5. Canvas Focus on Click
    const viewport = document.getElementById('viewport-container');
    if (viewport) {
      viewport.addEventListener('click', () => {
        window.focus();
        document.body.focus();
      });
    }
  }

  isTyping(e) {
    if (!e || !e.target) return false;
    const tag = e.target.tagName ? e.target.tagName.toLowerCase() : '';
    return tag === 'input' || tag === 'textarea';
  }

  resolveKeyName(e) {
    // Priority: code map -> key letter -> arrow key
    if (this.keyMap[e.code]) return this.keyMap[e.code];
    if (e.key) {
      const k = e.key.toLowerCase();
      if (k === 'w' || k === 'arrowup') return 'w';
      if (k === 's' || k === 'arrowdown') return 's';
      if (k === 'a' || k === 'arrowleft') return 'a';
      if (k === 'd' || k === 'arrowright') return 'd';
      if (k === 'q') return 'q';
      if (k === 'e') return 'e';
      if (k === 'r' || k === 'pageup') return 'r';
      if (k === 'f' || k === 'pagedown') return 'f';
      if (k === ' ' || k === 'space') return 'space';
      if (k === 'shift') return 'shift';
      if (k === 'control' || k === 'ctrl') return 'control';
      if (k === 't') return 'arm_toggle';
      if (k === 'h') return 'hover';
    }
    return null;
  }

  handleKeyDown(e) {
    if (this.isTyping(e)) return;

    const keyName = this.resolveKeyName(e);
    if (!keyName) return;

    // Prevent spacebar scrolling page or arrow key page scrolling
    if (e.code === 'Space' || e.key === ' ' || e.key.startsWith('Arrow') || ['KeyW', 'KeyS', 'KeyA', 'KeyD', 'KeyR', 'KeyF'].includes(e.code)) {
      e.preventDefault();
    }

    if (!this.keys[keyName]) {
      this.keys[keyName] = true;
      this.updateKeycapUI(keyName, true);

      if (keyName === 'space') {
        this.executeCommand('EMERGENCY_STOP');
      } else if (keyName === 'arm_toggle') {
        const btnArm = document.getElementById('btn-arm-toggle');
        const isArmed = btnArm?.dataset.armed === 'true';
        this.executeCommand(isArmed ? 'DISARM' : 'ARM');
      } else if (keyName === 'hover') {
        this.executeCommand('HOVER');
      } else {
        // Send movement KEY_DOWN (auto-arms in backend if disarmed)
        this.socket.sendCommand('KEY_DOWN', { key: keyName });
      }
    }
  }

  handleKeyUp(e) {
    if (this.isTyping(e)) return;

    const keyName = this.resolveKeyName(e);
    if (!keyName) return;

    if (this.keys[keyName]) {
      this.keys[keyName] = false;
      this.updateKeycapUI(keyName, false);
      if (keyName !== 'space' && keyName !== 'arm_toggle' && keyName !== 'hover') {
        this.socket.sendCommand('KEY_UP', { key: keyName });
      }
    }
  }

  setupInteractiveKeycaps() {
    const keyActions = ['w', 's', 'a', 'd', 'q', 'e', 'r', 'f'];
    keyActions.forEach(k => {
      const el = document.getElementById(`key-${k}`);
      if (!el) return;
      el.style.cursor = 'pointer';
      el.style.userSelect = 'none';

      const press = (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        if (!this.keys[k]) {
          this.keys[k] = true;
          this.updateKeycapUI(k, true);
          this.socket.sendCommand('KEY_DOWN', { key: k });
        }
      };

      const release = (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.keys[k]) {
          this.keys[k] = false;
          this.updateKeycapUI(k, false);
          this.socket.sendCommand('KEY_UP', { key: k });
        }
      };

      el.addEventListener('mousedown', press);
      el.addEventListener('mouseup', release);
      el.addEventListener('mouseleave', release);
      el.addEventListener('touchstart', press, { passive: false });
      el.addEventListener('touchend', release, { passive: false });
      el.addEventListener('touchcancel', release, { passive: false });
    });

    // Space keycap (E-Stop)
    const spaceEl = document.getElementById('key-space');
    if (spaceEl) {
      spaceEl.style.cursor = 'pointer';
      spaceEl.addEventListener('click', (ev) => {
        ev.preventDefault();
        this.executeCommand('EMERGENCY_STOP');
      });
    }

    // Shift keycap (Speed Boost)
    const shiftEl = document.getElementById('key-shift');
    if (shiftEl) {
      shiftEl.style.cursor = 'pointer';
      shiftEl.addEventListener('click', (ev) => {
        ev.preventDefault();
        this.socket.sendCommand('SET_SPEED_MOD', { mode: 'BOOST' });
        this.updateSpeedButtons('BOOST');
      });
    }

    // Ctrl keycap (Precision Speed)
    const ctrlEl = document.getElementById('key-ctrl');
    if (ctrlEl) {
      ctrlEl.style.cursor = 'pointer';
      ctrlEl.addEventListener('click', (ev) => {
        ev.preventDefault();
        this.socket.sendCommand('SET_SPEED_MOD', { mode: 'PRECISION' });
        this.updateSpeedButtons('PRECISION');
      });
    }
  }

  updateKeycapUI(key, isPressed) {
    const elId = `key-${key}`;
    const el = document.getElementById(elId);
    if (el) {
      if (isPressed) {
        el.classList.add('active');
      } else {
        el.classList.remove('active');
      }
    }
  }

  executeCommand(command, params = {}) {
    this.showCommandFeedback('pending');
    this.socket.sendCommand(command, params);

    // Timeout safety feedback
    if (this.commandTimeoutTimer) clearTimeout(this.commandTimeoutTimer);
    this.commandTimeoutTimer = setTimeout(() => {
      this.showCommandFeedback('timeout');
    }, 2500);
  }

  handleCommandAck(result) {
    if (this.commandTimeoutTimer) {
      clearTimeout(this.commandTimeoutTimer);
      this.commandTimeoutTimer = null;
    }
    if (result && result.status === 'ERROR') {
      this.showCommandFeedback('failure');
    } else {
      this.showCommandFeedback('success');
    }
  }

  showCommandFeedback(type) {
    const chip = document.getElementById('cmd-feedback-chip');
    if (!chip) return;

    chip.classList.remove('hidden', 'feedback-pending', 'feedback-success', 'feedback-failure');

    if (type === 'pending') {
      chip.classList.add('feedback-pending');
    } else if (type === 'success') {
      chip.classList.add('feedback-success');
      setTimeout(() => chip.classList.add('hidden'), 1500);
    } else {
      chip.classList.add('feedback-failure');
      setTimeout(() => chip.classList.add('hidden'), 2000);
    }
  }

  setupButtonListeners() {
    // Arm / Disarm toggle
    const btnArm = document.getElementById('btn-arm-toggle');
    if (btnArm) {
      btnArm.addEventListener('click', () => {
        const isArmed = btnArm.dataset.armed === 'true';
        this.executeCommand(isArmed ? 'DISARM' : 'ARM');
      });
    }

    // Emergency Stop (Always prominent & accessible)
    const btnEstop = document.getElementById('btn-emergency-stop');
    if (btnEstop) {
      btnEstop.addEventListener('click', () => {
        this.executeCommand('EMERGENCY_STOP');
      });
    }

    // Hover
    const btnHover = document.getElementById('btn-flight-hover');
    if (btnHover) {
      btnHover.addEventListener('click', () => {
        this.executeCommand('HOVER');
      });
    }

    // Land
    const btnLand = document.getElementById('btn-flight-land');
    if (btnLand) {
      btnLand.addEventListener('click', () => {
        this.executeCommand('LAND');
      });
    }

    // Return to Home
    const btnRth = document.getElementById('btn-flight-rth');
    if (btnRth) {
      btnRth.addEventListener('click', () => {
        this.executeCommand('RTH');
      });
    }

    // Reset Fault Button (From Fault Banner)
    const btnResetFault = document.getElementById('btn-reset-fault');
    if (btnResetFault) {
      btnResetFault.addEventListener('click', () => {
        this.executeCommand('RESET_FAULT');
      });
    }

    // Flight Mode Selector
    const modeSelect = document.getElementById('select-flight-mode');
    if (modeSelect) {
      modeSelect.addEventListener('change', (e) => {
        this.executeCommand('SET_MODE', { mode: e.target.value });
      });
    }

    // Speed Multiplier Buttons
    const btnSpeedNormal = document.getElementById('btn-speed-normal');
    const btnSpeedBoost = document.getElementById('btn-speed-boost');
    const btnSpeedPrec = document.getElementById('btn-speed-precision');

    if (btnSpeedNormal) {
      btnSpeedNormal.addEventListener('click', () => {
        this.socket.sendCommand('SET_SPEED_MOD', { mode: 'NORMAL' });
        this.updateSpeedButtons('NORMAL');
      });
    }
    if (btnSpeedBoost) {
      btnSpeedBoost.addEventListener('click', () => {
        this.socket.sendCommand('SET_SPEED_MOD', { mode: 'BOOST' });
        this.updateSpeedButtons('BOOST');
      });
    }
    if (btnSpeedPrec) {
      btnSpeedPrec.addEventListener('click', () => {
        this.socket.sendCommand('SET_SPEED_MOD', { mode: 'PRECISION' });
        this.updateSpeedButtons('PRECISION');
      });
    }
  }

  updateSpeedButtons(activeMode) {
    const modes = ['NORMAL', 'BOOST', 'PRECISION'];
    modes.forEach(m => {
      const btn = document.getElementById(`btn-speed-${m.toLowerCase()}`);
      if (btn) {
        if (m === activeMode) {
          btn.className = "py-0.5 px-2 rounded bg-amber-600 text-white font-bold text-[9px] shadow";
        } else {
          btn.className = "py-0.5 px-2 rounded bg-slate-800 text-slate-400 hover:bg-slate-700 font-semibold text-[9px]";
        }
      }
    });
  }

  setupAccordions() {
    const accordions = [
      { header: 'accordion-header-shortcuts', content: 'accordion-content-shortcuts', icon: 'accordion-icon-shortcuts' },
      { header: 'accordion-header-tof', content: 'accordion-content-tof', icon: 'accordion-icon-tof' },
      { header: 'accordion-header-system', content: 'accordion-content-system', icon: 'accordion-icon-system' }
    ];

    accordions.forEach(acc => {
      const headerEl = document.getElementById(acc.header);
      const contentEl = document.getElementById(acc.content);
      const iconEl = document.getElementById(acc.icon);

      if (headerEl && contentEl) {
        headerEl.addEventListener('click', () => {
          const isCollapsed = contentEl.classList.contains('collapsed');
          if (isCollapsed) {
            contentEl.classList.remove('collapsed');
            if (iconEl) iconEl.style.transform = 'rotate(0deg)';
          } else {
            contentEl.classList.add('collapsed');
            if (iconEl) iconEl.style.transform = 'rotate(-90deg)';
          }
        });
      }
    });
  }

  updateArmStateUI(isArmed) {
    const btnArm = document.getElementById('btn-arm-toggle');
    const btnArmText = document.getElementById('btn-arm-text');
    const btnHover = document.getElementById('btn-flight-hover');
    const btnRth = document.getElementById('btn-flight-rth');
    const btnLand = document.getElementById('btn-flight-land');

    if (btnArm) {
      btnArm.dataset.armed = isArmed ? 'true' : 'false';
      if (isArmed) {
        btnArm.className = "action-grid-btn btn-disarm-active";
        if (btnArmText) btnArmText.textContent = "DISARM";
      } else {
        btnArm.className = "action-grid-btn btn-arm-ready";
        if (btnArmText) btnArmText.textContent = "ARM DRONE";
      }
    }

    // Reflect arm state in flight action buttons
    if (btnHover) btnHover.disabled = !isArmed;
    if (btnRth) btnRth.disabled = !isArmed;
    if (btnLand) btnLand.disabled = !isArmed;
  }
}
