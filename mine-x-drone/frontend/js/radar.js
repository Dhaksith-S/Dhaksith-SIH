/**
 * MINE-X DRONE COMMAND - Geospatial Cavern Radar
 * Renders a top-down CAD radar blueprint showing the drone's position, heading,
 * mine tunnel corridor, station beacons, hazardous gas zones, and trailing flight path.
 */

class CavernRadar {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
    this.sweepAngle = 0;
    this.flightPath = [];
    this.maxPathPoints = 80;

    // Spline reference points for the 240m mine tunnel
    this.splineNodes = [
      { x: 0.0, z: 35.0 },
      { x: 0.0, z: 5.0 },
      { x: 10.0, z: -30.0 },
      { x: -14.0, z: -72.0 },
      { x: 16.0, z: -118.0 },
      { x: -5.0, z: -160.0 },
      { x: 0.0, z: -205.0 }
    ];

    this.stations = [
      { name: "Portal", x: 0, z: 25 },
      { name: "Timber", x: 10, z: -25 },
      { name: "Stope", x: -14, z: -72 },
      { name: "Chute", x: 16, z: -118 },
      { name: "Winze", x: -5, z: -160 }
    ];
  }

  update(dronePos, headingDeg) {
    if (!this.ctx || !this.canvas) return;

    const w = this.canvas.width;
    const h = this.canvas.height;
    const ctx = this.ctx;

    // Record breadcrumb
    if (dronePos) {
      if (this.flightPath.length === 0 ||
          Math.hypot(dronePos.x - this.flightPath[this.flightPath.length - 1].x,
                     dronePos.z - this.flightPath[this.flightPath.length - 1].z) > 1.5) {
        this.flightPath.push({ x: dronePos.x, z: dronePos.z });
        if (this.flightPath.length > this.maxPathPoints) {
          this.flightPath.shift();
        }
      }
    }

    ctx.clearRect(0, 0, w, h);

    // Coordinate mapping: map drone to center or scroll with drone
    const centerX = w / 2;
    const centerY = h / 2;
    const scale = 1.15; // pixels per meter

    const mapX = (x) => centerX + (x - (dronePos ? dronePos.x : 0)) * scale;
    const mapY = (z) => centerY - (z - (dronePos ? dronePos.z : 0)) * scale;

    // 1. Radar Range Rings & North Indicator
    ctx.strokeStyle = 'rgba(217, 119, 6, 0.18)';
    ctx.lineWidth = 1;
    [25, 50, 75].forEach(r => {
      ctx.beginPath();
      ctx.arc(centerX, centerY, r * scale, 0, Math.PI * 2);
      ctx.stroke();
    });

    // North Compass Label
    ctx.fillStyle = '#38bdf8';
    ctx.font = 'bold 9px "Share Tech Mono"';
    ctx.textAlign = 'center';
    ctx.fillText('N', centerX, centerY - (75 * scale) - 4);
    ctx.textAlign = 'left';

    // 2. Crosshairs
    ctx.strokeStyle = 'rgba(217, 119, 6, 0.12)';
    ctx.beginPath();
    ctx.moveTo(centerX, 0); ctx.lineTo(centerX, h);
    ctx.moveTo(0, centerY); ctx.lineTo(w, centerY);
    ctx.stroke();

    // 3. Wide Cavern Boundary (Tunnel Walls)
    ctx.strokeStyle = '#854d0e';
    ctx.lineWidth = 18 * scale * 0.9;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.beginPath();
    this.splineNodes.forEach((p, idx) => {
      const rx = mapX(p.x);
      const ry = mapY(p.z);
      if (idx === 0) ctx.moveTo(rx, ry);
      else ctx.lineTo(rx, ry);
    });
    ctx.stroke();

    // 4. Grand Extraction Stope Chamber Expansion
    ctx.fillStyle = 'rgba(180, 83, 9, 0.35)';
    ctx.beginPath();
    ctx.ellipse(mapX(-14), mapY(-72), 26 * scale, 20 * scale, 0, 0, Math.PI * 2);
    ctx.fill();

    // 5. High-Methane Gas Cloud Zone in Deep Winze (Z = -160)
    ctx.fillStyle = 'rgba(239, 68, 68, 0.22)';
    ctx.beginPath();
    ctx.ellipse(mapX(-5), mapY(-160), 22 * scale, 18 * scale, 0, 0, Math.PI * 2);
    ctx.fill();

    // 6. Safe Flight Corridor Core
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 3;
    ctx.beginPath();
    this.splineNodes.forEach((p, idx) => {
      const rx = mapX(p.x);
      const ry = mapY(p.z);
      if (idx === 0) ctx.moveTo(rx, ry);
      else ctx.lineTo(rx, ry);
    });
    ctx.stroke();

    // 7. Station Beacons
    this.stations.forEach((stn, i) => {
      const sx = mapX(stn.x);
      const sy = mapY(stn.z);
      ctx.fillStyle = (i === 2) ? '#10b981' : '#38bdf8';
      ctx.beginPath();
      ctx.arc(sx, sy, 3.5, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#a1a1aa';
      ctx.font = '8px "Share Tech Mono"';
      ctx.fillText(stn.name, sx + 6, sy + 3);
    });

    // 8. Flight Path Breadcrumb Trail
    if (this.flightPath.length > 1) {
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.45)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      this.flightPath.forEach((pt, i) => {
        const px = mapX(pt.x);
        const py = mapY(pt.z);
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.stroke();
    }

    // 9. Dynamic Radar Sweep Beam
    this.sweepAngle += 0.05;
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.35)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.lineTo(
      centerX + Math.cos(this.sweepAngle) * 75 * scale,
      centerY + Math.sin(this.sweepAngle) * 75 * scale
    );
    ctx.stroke();

    // 10. Drone Marker & Heading Indicator (at center)
    const hdgRad = THREE.MathUtils.degToRad(headingDeg || 0);
    // Heading in our coordinate: 0 is North/East, vector forward
    const hx = Math.sin(hdgRad);
    const hy = -Math.cos(hdgRad);

    // Sensor Field of View cone
    ctx.fillStyle = 'rgba(245, 158, 11, 0.18)';
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    const leftAngle = hdgRad - 0.45;
    const rightAngle = hdgRad + 0.45;
    ctx.lineTo(centerX + Math.sin(leftAngle) * 28, centerY - Math.cos(leftAngle) * 28);
    ctx.lineTo(centerX + Math.sin(rightAngle) * 28, centerY - Math.cos(rightAngle) * 28);
    ctx.closePath();
    ctx.fill();

    // Drone Marker Circle & Arrow
    ctx.fillStyle = '#f59e0b';
    ctx.beginPath();
    ctx.arc(centerX, centerY, 4.5, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.lineTo(centerX + hx * 12, centerY + hy * 12);
    ctx.stroke();
  }
}
