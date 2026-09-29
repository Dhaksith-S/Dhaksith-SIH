/**
 * MINE-X DRONE COMMAND - 3D Mine Cavern & Drone Visualization Engine
 * Implements Three.js subterranean environment, procedural terracotta rock geometry,
 * high-detail quadcopter drone model with rolling protective cage, dynamic propellers,
 * navigation LEDs, searchlight, LiDAR point cloud, and 3D volumetric gas plumes.
 */

class Drone3DEngine {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.orbitControls = null;

    // Groups & Meshes
    this.cavernGroup = null;
    this.rockMesh = null;
    this.wireframeMesh = null;
    this.pointCloudMesh = null;
    this.timberGroup = null;
    this.railGroup = null;
    this.corridorGroup = null;
    this.gridGroup = null;
    this.markerGroup = null;
    this.gasPlumeGroup = null;
    this.surveySpotlights = [];

    // Drone 3D Model (Decoupled Spherical Cage & Gimbal Core)
    this.droneGroup = null;
    this.outerCageGroup = null;
    this.innerCoreGroup = null;
    this.props = [];
    this.strobeLed = null;
    this.locatorMarker = null;

    // Cavern spline
    this.cavernSpline = null;

    // Camera Modes: 'OVERVIEW', 'FOLLOW', 'CAMERA', 'TOP'
    this.cameraMode = 'OVERVIEW';

    // Drone state targets for smooth lerping
    this.dronePos = new THREE.Vector3(0, 1.35, 25);
    this.prevDronePos = new THREE.Vector3(0, 1.35, 25);
    this.droneRot = new THREE.Euler(0, Math.PI, 0, 'YXZ');
    this.cageRollAngle = 0;
    this.cageRadius = 1.35;
    this.propSpeed = 0;
    this.motorRPMs = [0, 0, 0, 0];
    this.armed = false;
    this.motionMode = 'DISARMED';
    this.groundContact = true;

    // Gas Plume particles
    this.gasParticles = null;

    this.init();
  }

  init() {
    const w = this.container.clientWidth || window.innerWidth;
    const h = this.container.clientHeight || window.innerHeight;

    // 1. Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x050404);
    this.scene.fog = new THREE.FogExp2(0x090706, 0.0085);

    // 2. Camera
    this.camera = new THREE.PerspectiveCamera(65, w / h, 0.1, 900);
    this.camera.position.set(0, 22, 55);

    // 3. Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.35;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.container.appendChild(this.renderer.domElement);

    // 4. OrbitControls
    this.orbitControls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
    this.orbitControls.enableDamping = true;
    this.orbitControls.dampingFactor = 0.08;
    this.orbitControls.maxDistance = 350;
    this.orbitControls.minDistance = 1.5;
    this.orbitControls.target.set(0, 4.5, 25);

    // 5. Environmental Lighting
    const ambientLight = new THREE.AmbientLight(0x4a3227, 0.75);
    this.scene.add(ambientLight);

    const sunSurvey = new THREE.DirectionalLight(0xffbe76, 1.25);
    sunSurvey.position.set(25, 65, 45);
    sunSurvey.castShadow = true;
    this.scene.add(sunSurvey);

    // 6. Build Environment
    this.buildCavernSpline();
    this.buildCavernGeometry();
    this.buildLidarPointCloud();
    this.buildFlightCorridors();
    this.buildTimberArchways();
    this.buildHaulageRailsAndPipes();
    this.buildSpatialGridAndPins();
    this.setupSurveyLighting();
    this.buildVolumetricGasPlume();

    // 7. Build 3D Quadcopter Drone Model
    this.buildDroneModel();

    // 8. Event Listeners
    window.addEventListener('resize', () => this.onResize());

    // 9. Start Render Loop
    this.animate();
  }

  buildCavernSpline() {
    const splinePoints = [
      new THREE.Vector3(0, 4.0, 35),       // Portal mouth
      new THREE.Vector3(0, 5.0, 5),        // Entrance throat
      new THREE.Vector3(10.0, 6.5, -30),   // Western bend
      new THREE.Vector3(-14.0, 9.5, -72),  // Center of Great Stope Dome
      new THREE.Vector3(16.0, 8.0, -118),  // North-East Ore Chute
      new THREE.Vector3(-5.0, 4.5, -160),  // Deep winze descent
      new THREE.Vector3(0, 0.0, -205)      // Deep winze terminus
    ];
    this.cavernSpline = new THREE.CatmullRomCurve3(splinePoints);
  }

  createProceduralRockTexture(type = 'color') {
    const size = 1024;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');

    if (type === 'color') {
      ctx.fillStyle = '#653828';
      ctx.fillRect(0, 0, size, size);

      for (let i = 0; i < 28000; i++) {
        const x = Math.random() * size;
        const y = Math.random() * size;
        const r = Math.random() * 4.2 + 0.8;
        const rand = Math.random();

        if (rand < 0.35) {
          ctx.fillStyle = `rgba(180, 88, 54, ${Math.random() * 0.55})`;
        } else if (rand < 0.65) {
          ctx.fillStyle = `rgba(40, 20, 14, ${Math.random() * 0.75})`;
        } else if (rand < 0.85) {
          ctx.fillStyle = `rgba(224, 162, 120, ${Math.random() * 0.4})`;
        } else {
          ctx.fillStyle = `rgba(118, 56, 36, ${Math.random() * 0.5})`;
        }
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }

      for (let j = 0; j < 80; j++) {
        let cx = Math.random() * size;
        let cy = Math.random() * size;
        ctx.strokeStyle = 'rgba(24, 12, 10, 0.75)';
        ctx.lineWidth = Math.random() * 2.5 + 1.0;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        for (let seg = 0; seg < 8; seg++) {
          cx += (Math.random() - 0.5) * 65;
          cy += (Math.random() - 0.5) * 65;
          ctx.lineTo(cx, cy);
        }
        ctx.stroke();
      }
    } else {
      ctx.fillStyle = '#808080';
      ctx.fillRect(0, 0, size, size);
      for (let i = 0; i < 20000; i++) {
        const x = Math.random() * size;
        const y = Math.random() * size;
        const r = Math.random() * 5.0 + 1.0;
        const val = Math.floor(Math.random() * 255);
        ctx.fillStyle = `rgba(${val}, ${val}, ${val}, ${Math.random() * 0.4})`;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    return texture;
  }

  buildCavernGeometry() {
    this.cavernGroup = new THREE.Group();

    const tubularSegments = 180;
    const baseRadius = 17.0;
    const radialSegments = 36;
    const tubeGeo = new THREE.TubeGeometry(this.cavernSpline, tubularSegments, baseRadius, radialSegments, false);

    const pos = tubeGeo.attributes.position;
    const v = new THREE.Vector3();

    for (let i = 0; i < pos.count; i++) {
      v.fromBufferAttribute(pos, i);

      let cavernExpansion = 1.0;
      if (v.z < -45 && v.z > -100) {
        cavernExpansion = 1.55 + Math.sin((v.z + 45) / 55 * Math.PI) * 0.85;
      }

      const n1 = Math.sin(v.x * 0.22 + v.z * 0.14) * 2.0;
      const n2 = Math.cos(v.y * 0.32 + v.z * 0.22) * 1.6;
      const n3 = Math.sin((v.x + v.y + v.z) * 0.65) * 1.0;
      const rockFracture = n1 + n2 + n3;

      if (v.y < 1.2) {
        v.y = 0.0 + Math.sin(v.z * 0.25) * 0.3;
        v.x *= cavernExpansion * 1.2;
      } else {
        v.x = (v.x * cavernExpansion) + rockFracture * 1.4;
        v.y = (v.y * (cavernExpansion > 1.2 ? 1.6 : 1.15)) + rockFracture * 1.5;
      }

      pos.setXYZ(i, v.x, v.y, v.z);
    }
    tubeGeo.computeVertexNormals();

    const rockColorMap = this.createProceduralRockTexture('color');
    rockColorMap.repeat.set(18, 12);
    const rockBumpMap = this.createProceduralRockTexture('bump');
    rockBumpMap.repeat.set(18, 12);

    const rockMat = new THREE.MeshStandardMaterial({
      map: rockColorMap,
      bumpMap: rockBumpMap,
      bumpScale: 0.5,
      roughness: 0.88,
      metalness: 0.10,
      side: THREE.BackSide
    });

    this.rockMesh = new THREE.Mesh(tubeGeo, rockMat);
    this.rockMesh.receiveShadow = true;
    this.cavernGroup.add(this.rockMesh);

    // Wireframe Mesh for X-Ray
    const wireMat = new THREE.MeshBasicMaterial({
      color: 0xf59e0b,
      wireframe: true,
      transparent: true,
      opacity: 0.25
    });
    this.wireframeMesh = new THREE.Mesh(tubeGeo, wireMat);
    this.wireframeMesh.visible = false;
    this.cavernGroup.add(this.wireframeMesh);

    // Central Pillar in Stope (Z = -72)
    const pillarGeo = new THREE.CylinderGeometry(5.0, 8.5, 26, 20);
    const pPos = pillarGeo.attributes.position;
    for (let k = 0; k < pPos.count; k++) {
      pPos.setX(k, pPos.getX(k) + (Math.random() - 0.5) * 1.8);
      pPos.setZ(k, pPos.getZ(k) + (Math.random() - 0.5) * 1.8);
    }
    pillarGeo.computeVertexNormals();
    const pillarMat = new THREE.MeshStandardMaterial({
      map: rockColorMap,
      bumpMap: rockBumpMap,
      bumpScale: 0.45,
      roughness: 0.92
    });
    const pillar = new THREE.Mesh(pillarGeo, pillarMat);
    pillar.position.set(-7, 13, -72);
    pillar.castShadow = true;
    this.cavernGroup.add(pillar);

    // Boulders
    const boulderSpawns = [
      { x: -8, y: 3.0, z: 15, s: 5.5 },
      { x: 11, y: 3.5, z: -16, s: 7.2 },
      { x: -16, y: 4.5, z: -62, s: 10.5 },
      { x: 14, y: 3.8, z: -82, s: 7.8 },
      { x: 5, y: 3.2, z: -135, s: 6.2 }
    ];
    boulderSpawns.forEach(b => {
      const bGeo = new THREE.DodecahedronGeometry(1.0, 1);
      const bMesh = new THREE.Mesh(bGeo, pillarMat);
      bMesh.scale.set(b.s, b.s * 0.75, b.s);
      bMesh.position.set(b.x, b.y, b.z);
      bMesh.rotation.set(Math.random() * 3, Math.random() * 3, 0);
      bMesh.castShadow = true;
      this.cavernGroup.add(bMesh);
    });

    this.scene.add(this.cavernGroup);
  }

  buildLidarPointCloud() {
    const count = 22000;
    const geo = new THREE.BufferGeometry();
    const pos = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);

    const splinePoints = this.cavernSpline.getPoints(140);

    for (let i = 0; i < count; i++) {
      const idx = Math.floor(Math.random() * (splinePoints.length - 1));
      const center = splinePoints[idx];

      const angle = Math.random() * Math.PI * 2;
      const radius = 15 + Math.random() * 9;
      const px = center.x + Math.cos(angle) * radius;
      const py = Math.max(0.1, center.y + Math.sin(angle) * (radius * 0.88));
      const pz = center.z + (Math.random() - 0.5) * 4.5;

      pos[i * 3] = px;
      pos[i * 3 + 1] = py;
      pos[i * 3 + 2] = pz;

      const depthNorm = Math.abs(pz) / 220;
      colors[i * 3] = 0.2 + depthNorm * 0.8;
      colors[i * 3 + 1] = 0.85 - depthNorm * 0.45;
      colors[i * 3 + 2] = 0.95 - depthNorm * 0.65;
    }

    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const pMat = new THREE.PointsMaterial({
      size: 0.28,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending
    });

    this.pointCloudMesh = new THREE.Points(geo, pMat);
    this.scene.add(this.pointCloudMesh);
  }

  buildFlightCorridors() {
    this.corridorGroup = new THREE.Group();

    const corridorGeo = new THREE.TubeGeometry(this.cavernSpline, 95, 5.8, 16, false);
    const corridorMat = new THREE.MeshBasicMaterial({
      color: 0x10b981,
      wireframe: true,
      transparent: true,
      opacity: 0.18
    });
    const corridorMesh = new THREE.Mesh(corridorGeo, corridorMat);
    this.corridorGroup.add(corridorMesh);

    const waypoints = this.cavernSpline.getPoints(16);
    waypoints.forEach(pt => {
      const ringGeo = new THREE.TorusGeometry(5.8, 0.12, 8, 24);
      const ringMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.65 });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.copy(pt);
      this.corridorGroup.add(ring);
    });

    this.scene.add(this.corridorGroup);
  }

  buildTimberArchways() {
    this.timberGroup = new THREE.Group();
    const timberMat = new THREE.MeshStandardMaterial({
      color: 0xb87a42,
      roughness: 0.85
    });

    const timberZPoints = [18, -4, -25, -48, -98, -125];

    timberZPoints.forEach(zVal => {
      const arch = new THREE.Group();
      const gateWidth = 22.0;
      const gateHeight = 13.0;
      const postThickness = 1.0;

      const leftPost = new THREE.Mesh(new THREE.BoxGeometry(postThickness, gateHeight, postThickness), timberMat);
      leftPost.position.set(-gateWidth / 2, gateHeight / 2, 0);
      arch.add(leftPost);

      const rightPost = new THREE.Mesh(new THREE.BoxGeometry(postThickness, gateHeight, postThickness), timberMat);
      rightPost.position.set(gateWidth / 2, gateHeight / 2, 0);
      arch.add(rightPost);

      const beam = new THREE.Mesh(new THREE.BoxGeometry(gateWidth + 1.8, postThickness * 1.1, postThickness * 1.2), timberMat);
      beam.position.set(0, gateHeight, 0);
      arch.add(beam);

      const lantern = new THREE.Mesh(
        new THREE.CylinderGeometry(0.35, 0.45, 0.85, 8),
        new THREE.MeshStandardMaterial({ color: 0xf59e0b, emissive: 0xd97706, emissiveIntensity: 1.6 })
      );
      lantern.position.set(0, gateHeight - 1.0, 0);
      arch.add(lantern);

      const lLight = new THREE.PointLight(0xffa133, 1.8, 30);
      lLight.position.set(0, gateHeight - 1.3, 0);
      arch.add(lLight);

      const centerPt = this.cavernSpline.getPointAt(Math.min(1.0, Math.max(0.0, (18 - zVal) / 240)));
      arch.position.set(centerPt.x, 0, zVal);
      this.timberGroup.add(arch);
    });

    this.scene.add(this.timberGroup);
  }

  buildHaulageRailsAndPipes() {
    this.railGroup = new THREE.Group();
    const steelMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.85, roughness: 0.3 });
    const sleeperMat = new THREE.MeshStandardMaterial({ color: 0x3d271d, roughness: 0.92 });

    const trackOffsets = [-3.2, -1.3, 1.3, 3.2];
    const pts = this.cavernSpline.getPoints(95);

    trackOffsets.forEach(offX => {
      const railCurvePts = pts.map(p => new THREE.Vector3(p.x + offX, 0.16, p.z));
      const railCurve = new THREE.CatmullRomCurve3(railCurvePts);
      const railGeo = new THREE.TubeGeometry(railCurve, 95, 0.08, 6, false);
      const rail = new THREE.Mesh(railGeo, steelMat);
      this.railGroup.add(rail);
    });

    for (let s = 0; s < pts.length; s += 2) {
      const pt = pts[s];
      const sleeper = new THREE.Mesh(new THREE.BoxGeometry(7.8, 0.15, 0.42), sleeperMat);
      sleeper.position.set(pt.x, 0.07, pt.z);
      this.railGroup.add(sleeper);
    }

    const ventPts = pts.map(p => new THREE.Vector3(p.x - 8.0, 15.0, p.z));
    const ventCurve = new THREE.CatmullRomCurve3(ventPts);
    const ventGeo = new THREE.TubeGeometry(ventCurve, 75, 0.9, 12, false);
    const ventMat = new THREE.MeshStandardMaterial({ color: 0xeab308, roughness: 0.55 });
    const ventDuct = new THREE.Mesh(ventGeo, ventMat);
    this.railGroup.add(ventDuct);

    this.scene.add(this.railGroup);
  }

  buildSpatialGridAndPins() {
    this.gridGroup = new THREE.Group();
    this.markerGroup = new THREE.Group();

    const gridHelper = new THREE.GridHelper(280, 28, 0xd97706, 0x27272a);
    gridHelper.position.set(0, 0.01, -85);
    this.gridGroup.add(gridHelper);
    this.scene.add(this.gridGroup);

    const stationTargets = [
      new THREE.Vector3(0, 5, 18),
      new THREE.Vector3(2, 6, -25),
      new THREE.Vector3(-6, 12, -72),
      new THREE.Vector3(-4, 7, -118),
      new THREE.Vector3(0, 0, -168)
    ];

    stationTargets.forEach((tgt, idx) => {
      const beacon = new THREE.Group();
      const pinGeo = new THREE.OctahedronGeometry(1.7, 0);
      const pinMat = new THREE.MeshStandardMaterial({
        color: idx === 2 ? 0x10b981 : 0x38bdf8,
        emissive: idx === 2 ? 0x059669 : 0x0284c7,
        emissiveIntensity: 0.85,
        metalness: 0.5,
        roughness: 0.2
      });
      const pinMesh = new THREE.Mesh(pinGeo, pinMat);
      pinMesh.position.y = 9.0;
      beacon.add(pinMesh);

      const lineGeo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(0, 9.0, 0)
      ]);
      const lineMat = new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.75 });
      const line = new THREE.Line(lineGeo, lineMat);
      beacon.add(line);

      beacon.position.copy(tgt);
      this.markerGroup.add(beacon);
    });

    this.scene.add(this.markerGroup);
  }

  setupSurveyLighting() {
    const lightPositions = [
      new THREE.Vector3(0, 18, 22),
      new THREE.Vector3(0, 22, -30),
      new THREE.Vector3(0, 26, -72),
      new THREE.Vector3(0, 20, -120),
      new THREE.Vector3(0, 16, -170)
    ];

    lightPositions.forEach(lp => {
      const spot = new THREE.SpotLight(0xffbe76, 2.5, 75, Math.PI / 3, 0.5, 1.2);
      spot.position.copy(lp);
      spot.target.position.set(lp.x, 0, lp.z);
      this.scene.add(spot.target);
      this.scene.add(spot);
      this.surveySpotlights.push(spot);
    });
  }

  buildVolumetricGasPlume() {
    // 3D Volumetric Gas Plume around Deep Winze Shaft (Z = -160)
    this.gasPlumeGroup = new THREE.Group();
    const particleCount = 600;
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 22;
      positions[i * 3 + 1] = Math.random() * 14 + 1.0;
      positions[i * 3 + 2] = -160 + (Math.random() - 0.5) * 35;

      // High methane yellow-orange plume
      colors[i * 3] = 0.95 + Math.random() * 0.05;      // R
      colors[i * 3 + 1] = 0.65 + Math.random() * 0.25;  // G
      colors[i * 3 + 2] = 0.05;                         // B
    }

    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const mat = new THREE.PointsMaterial({
      size: 1.8,
      vertexColors: true,
      transparent: true,
      opacity: 0.45,
      blending: THREE.AdditiveBlending
    });

    this.gasParticles = new THREE.Points(geo, mat);
    this.gasPlumeGroup.add(this.gasParticles);
    this.scene.add(this.gasPlumeGroup);
  }

  // ==========================================
  // HIGH-DETAIL 3D DRONE MODEL WITH PROTECTIVE ROLLING CAGE
  // ==========================================
  buildDroneModel() {
    this.droneGroup = new THREE.Group();
    this.droneGroup.position.copy(this.dronePos);
    this.droneGroup.rotation.order = 'YXZ';

    const CAGE_RADIUS = 1.35;
    this.cageRadius = CAGE_RADIUS;

    // ----------------------------------------------------
    // MATERIALS PALETTE (Industrial Subterranean Inspection Drone)
    // ----------------------------------------------------
    const MAT = {
      carbonStrut: new THREE.MeshStandardMaterial({
        color: 0x1a1d22,
        roughness: 0.35,
        metalness: 0.75
      }),
      carbonGloss: new THREE.MeshStandardMaterial({
        color: 0x111317,
        roughness: 0.25,
        metalness: 0.5
      }),
      cageJoint: new THREE.MeshStandardMaterial({
        color: 0xff6a13, // Anodized orange aluminum gusset node brackets
        roughness: 0.3,
        metalness: 0.8
      }),
      aluMatte: new THREE.MeshStandardMaterial({
        color: 0x94a3b8,
        roughness: 0.35,
        metalness: 0.85
      }),
      goldDome: new THREE.MeshStandardMaterial({
        color: 0xd97706, // Brass/Gold top antenna puck dome seen in video
        roughness: 0.2,
        metalness: 0.95
      }),
      lensGlass: new THREE.MeshStandardMaterial({
        color: 0x0284c7, // Anti-reflective coated camera lens
        roughness: 0.05,
        metalness: 0.95,
        emissive: 0x0369a1,
        emissiveIntensity: 0.35
      }),
      headlightHousing: new THREE.MeshStandardMaterial({
        color: 0x0f172a,
        roughness: 0.4,
        metalness: 0.6
      }),
      propBlade: new THREE.MeshStandardMaterial({
        color: 0xe2e8f0,
        roughness: 0.3,
        metalness: 0.1,
        transparent: true,
        opacity: 0.85
      }),
      driveRing: new THREE.MeshStandardMaterial({
        color: 0x334155,
        roughness: 0.4,
        metalness: 0.8
      }),
      beaconMarker: new THREE.MeshStandardMaterial({
        color: 0x38bdf8,
        emissive: 0x0284c7,
        emissiveIntensity: 0.9,
        roughness: 0.1
      })
    };

    // ====================================================
    // 1. OUTER SPHERICAL PROTECTIVE CAGE (Free-Rolling)
    // ====================================================
    this.outerCageGroup = new THREE.Group();

    // Geodesic spherical cage mesh with open dark ribs
    const icosaGeo = new THREE.IcosahedronGeometry(CAGE_RADIUS, 2);
    const cageWireframe = new THREE.Mesh(
      icosaGeo,
      new THREE.MeshStandardMaterial({
        color: 0x1e242d,
        roughness: 0.35,
        metalness: 0.8,
        wireframe: true
      })
    );
    this.outerCageGroup.add(cageWireframe);

    // Reinforcing circular rib rings (Equatorial + Meridian rings)
    const ribRingGeo = new THREE.TorusGeometry(CAGE_RADIUS, 0.022, 10, 48);

    // Ring 1: Equator (Horizontal)
    const ringEquator = new THREE.Mesh(ribRingGeo, MAT.carbonStrut);
    ringEquator.rotation.x = Math.PI / 2;
    this.outerCageGroup.add(ringEquator);

    // Ring 2: Prime Meridian (Vertical X-Y)
    const ringMeridian1 = new THREE.Mesh(ribRingGeo, MAT.carbonStrut);
    this.outerCageGroup.add(ringMeridian1);

    // Ring 3: Orthogonal Meridian (Vertical Y-Z)
    const ringMeridian2 = new THREE.Mesh(ribRingGeo, MAT.carbonStrut);
    ringMeridian2.rotation.y = Math.PI / 2;
    this.outerCageGroup.add(ringMeridian2);

    // Ring 4 & 5: 45-degree diagonal carbon reinforcement hoops
    const ringDiag1 = new THREE.Mesh(ribRingGeo, MAT.carbonStrut);
    ringDiag1.rotation.y = Math.PI / 4;
    this.outerCageGroup.add(ringDiag1);

    const ringDiag2 = new THREE.Mesh(ribRingGeo, MAT.carbonStrut);
    ringDiag2.rotation.y = -Math.PI / 4;
    this.outerCageGroup.add(ringDiag2);

    // Structural node gussets (anodized orange brackets at rib intersections)
    const nodeAngles = [
      [0, 1, 0], [0, -1, 0],
      [1, 0, 0], [-1, 0, 0],
      [0, 0, 1], [0, 0, -1],
      [0.707, 0, 0.707], [-0.707, 0, 0.707],
      [0.707, 0, -0.707], [-0.707, 0, -0.707],
      [0, 0.707, 0.707], [0, -0.707, 0.707],
      [0, 0.707, -0.707], [0, -0.707, -0.707]
    ];
    nodeAngles.forEach(([nx, ny, nz]) => {
      const node = new THREE.Mesh(new THREE.BoxGeometry(0.065, 0.065, 0.065), MAT.cageJoint);
      node.position.set(nx * CAGE_RADIUS, ny * CAGE_RADIUS, nz * CAGE_RADIUS);
      this.outerCageGroup.add(node);
    });

    // Compact Concealed Ground Drive Mechanism
    // Internal drive track ring near bottom equator (NO large hanging wheels!)
    const driveTrack = new THREE.Mesh(
      new THREE.TorusGeometry(CAGE_RADIUS * 0.96, 0.018, 8, 36),
      MAT.driveRing
    );
    driveTrack.rotation.x = Math.PI / 2;
    driveTrack.position.y = -0.15;
    this.outerCageGroup.add(driveTrack);

    this.droneGroup.add(this.outerCageGroup);

    // ====================================================
    // 2. INNER CORE GIMBAL GROUP (Upright Stabilized)
    // ====================================================
    this.innerCoreGroup = new THREE.Group();

    // Central Avionics Pod / Body
    // Lower carbon deck
    const chassisBase = new THREE.Mesh(new THREE.CylinderGeometry(0.46, 0.48, 0.12, 24), MAT.carbonGloss);
    chassisBase.position.y = -0.04;
    this.innerCoreGroup.add(chassisBase);

    // Upper avionics enclosure
    const chassisTop = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.46, 0.14, 24), MAT.carbonStrut);
    chassisTop.position.y = 0.09;
    this.innerCoreGroup.add(chassisTop);

    // Top Brass/Gold Satellite/Antenna Dome Puck (as seen in video)
    const goldDomePuck = new THREE.Mesh(
      new THREE.SphereGeometry(0.24, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2),
      MAT.goldDome
    );
    goldDomePuck.position.y = 0.16;
    this.innerCoreGroup.add(goldDomePuck);

    const domeCollar = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.26, 0.04, 20), MAT.aluMatte);
    domeCollar.position.y = 0.17;
    this.innerCoreGroup.add(domeCollar);

    // Concealed Micro-Actuator Ground Drive Motor Housing
    // Tucked flush underneath chassis towards the bottom cage ring
    const driveActuator = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.08, 0.28), MAT.carbonStrut);
    driveActuator.position.set(0, -0.14, 0);
    this.innerCoreGroup.add(driveActuator);

    // 4 Carbon Arms & Brushless Motor Pods
    const armAngles = [Math.PI / 4, 3 * Math.PI / 4, 5 * Math.PI / 4, 7 * Math.PI / 4];
    const armRadius = 0.82; // Comfortably inside cage radius 1.35m

    this.props = [];
    armAngles.forEach((angle, idx) => {
      const arm = new THREE.Group();
      arm.rotation.y = angle;

      // Carbon Arm Spar
      const armSpar = new THREE.Mesh(new THREE.BoxGeometry(armRadius, 0.045, 0.065), MAT.carbonStrut);
      armSpar.position.set(armRadius / 2, 0.04, 0);
      arm.add(armSpar);

      // Motor Stator & Bell
      const mx = armRadius;
      const motorStator = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 0.08, 16), MAT.carbonStrut);
      motorStator.position.set(mx, 0.08, 0);
      arm.add(motorStator);

      const motorBell = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.10, 16), MAT.cageJoint);
      motorBell.position.set(mx, 0.16, 0);
      arm.add(motorBell);

      // Propeller Assembly
      const propGroup = new THREE.Group();
      propGroup.position.set(mx, 0.22, 0);

      const propNut = new THREE.Mesh(new THREE.ConeGeometry(0.045, 0.07, 12), MAT.aluMatte);
      propNut.position.y = 0.035;
      propGroup.add(propNut);

      // 2-Blade Carbon Propeller
      const blade1 = new THREE.Mesh(new THREE.BoxGeometry(0.58, 0.015, 0.08), MAT.propBlade);
      blade1.position.x = 0.29;
      blade1.rotation.z = 0.10;
      propGroup.add(blade1);

      const blade2 = new THREE.Mesh(new THREE.BoxGeometry(0.58, 0.015, 0.08), MAT.propBlade);
      blade2.position.x = -0.29;
      blade2.rotation.z = -0.10;
      propGroup.add(blade2);

      // Semi-transparent Propeller Blur Disc (fades in when spinning)
      const blurDisc = new THREE.Mesh(
        new THREE.CircleGeometry(0.58, 24).rotateX(-Math.PI / 2),
        new THREE.MeshBasicMaterial({
          color: 0x94a3b8,
          transparent: true,
          opacity: 0.0,
          side: THREE.DoubleSide
        })
      );
      blurDisc.position.y = 0.02;
      propGroup.add(blurDisc);

      arm.add(propGroup);
      this.innerCoreGroup.add(arm);

      this.props.push({
        group: propGroup,
        blurDisc: blurDisc,
        dir: (idx % 2 === 0) ? 1 : -1
      });
    });

    // Forward-Facing Optical Inspection Camera (Level & Upright)
    const camGroup = new THREE.Group();
    camGroup.position.set(0, -0.02, -0.48);

    const camHousing = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.18, 0.22), MAT.carbonGloss);
    camGroup.add(camHousing);

    const lensBezel = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.09, 0.08, 20).rotateX(Math.PI / 2), MAT.aluMatte);
    lensBezel.position.z = -0.12;
    camGroup.add(lensBezel);

    const glassLens = new THREE.Mesh(new THREE.CircleGeometry(0.075, 20), MAT.lensGlass);
    glassLens.position.z = -0.162;
    camGroup.add(glassLens);

    this.innerCoreGroup.add(camGroup);

    // Twin High-Power Inspection Headlights & Volumetric Light Cones
    const headlightBeamMat = new THREE.MeshBasicMaterial({
      color: 0xfff3d6,
      transparent: true,
      opacity: 0.22,
      side: THREE.DoubleSide
    });

    [-0.32, 0.32].forEach((hx) => {
      // Housing
      const lamp = new THREE.Mesh(new THREE.CylinderGeometry(0.065, 0.08, 0.12, 16).rotateX(Math.PI / 2), MAT.headlightHousing);
      lamp.position.set(hx, 0.0, -0.46);
      this.innerCoreGroup.add(lamp);

      // Glowing front emitter disc
      const emitter = new THREE.Mesh(new THREE.CircleGeometry(0.065, 16), new THREE.MeshBasicMaterial({ color: 0xfffbeb }));
      emitter.position.set(hx, 0.0, -0.522);
      this.innerCoreGroup.add(emitter);

      // Three.js SpotLight casting dynamic illumination into the mine cavern
      const spot = new THREE.SpotLight(0xfff5e6, 3.2, 50, Math.PI / 4.8, 0.45, 1.2);
      spot.position.set(hx, 0.0, -0.52);
      const spotTarget = new THREE.Object3D();
      spotTarget.position.set(hx * 1.5, -0.5, -28.0);
      this.innerCoreGroup.add(spotTarget);
      spot.target = spotTarget;
      this.innerCoreGroup.add(spot);

      // Volumetric visible light cone
      const coneGeo = new THREE.ConeGeometry(2.5, 14.0, 16, 1, true);
      coneGeo.rotateX(-Math.PI / 2);
      coneGeo.translate(0, 0, -7.0);
      const coneMesh = new THREE.Mesh(coneGeo, headlightBeamMat);
      coneMesh.position.set(hx, 0.0, -0.52);
      this.innerCoreGroup.add(coneMesh);
    });

    // Navigation LEDs
    // Red Port (Left)
    const navRed = new THREE.Mesh(new THREE.SphereGeometry(0.04, 8, 8), new THREE.MeshBasicMaterial({ color: 0xef4444 }));
    navRed.position.set(-0.62, 0.10, -0.62);
    this.innerCoreGroup.add(navRed);

    // Green Starboard (Right)
    const navGreen = new THREE.Mesh(new THREE.SphereGeometry(0.04, 8, 8), new THREE.MeshBasicMaterial({ color: 0x10b981 }));
    navGreen.position.set(0.62, 0.10, -0.62);
    this.innerCoreGroup.add(navGreen);

    // Cyan Strobe Rear
    this.strobeLed = new THREE.Mesh(new THREE.SphereGeometry(0.045, 8, 8), new THREE.MeshBasicMaterial({ color: 0x38bdf8 }));
    this.strobeLed.position.set(0, 0.16, 0.52);
    this.innerCoreGroup.add(this.strobeLed);

    // Top Floating Locator Diamond Marker (Ensures instant visibility at overview zoom)
    const markerGeo = new THREE.OctahedronGeometry(0.28, 0);
    this.locatorMarker = new THREE.Mesh(markerGeo, MAT.beaconMarker);
    this.locatorMarker.position.set(0, CAGE_RADIUS + 0.45, 0);
    this.innerCoreGroup.add(this.locatorMarker);

    this.droneGroup.add(this.innerCoreGroup);

    this.scene.add(this.droneGroup);

    // Setup camera pill buttons
    this.setupCameraPillButtons();
  }

  setupCameraPillButtons() {
    const btnOverview = document.getElementById('btn-view-overview');
    const btnFollow = document.getElementById('btn-view-follow');
    const btnCam = document.getElementById('btn-view-cam');

    if (btnOverview) {
      btnOverview.addEventListener('click', () => {
        this.setCameraView('OVERVIEW');
        this.updatePillActive('btn-view-overview');
      });
    }
    if (btnFollow) {
      btnFollow.addEventListener('click', () => {
        this.setCameraView('FOLLOW');
        this.updatePillActive('btn-view-follow');
      });
    }
    if (btnCam) {
      btnCam.addEventListener('click', () => {
        const pip = document.getElementById('camera-pip-card');
        if (pip) {
          pip.classList.toggle('hidden');
        }
        this.updatePillActive('btn-view-cam');
      });
    }

    const pipClose = document.getElementById('btn-pip-close');
    if (pipClose) {
      pipClose.addEventListener('click', () => {
        const pip = document.getElementById('camera-pip-card');
        if (pip) pip.classList.add('hidden');
      });
    }
  }

  updatePillActive(activeId) {
    ['btn-view-overview', 'btn-view-follow', 'btn-view-cam'].forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        if (id === activeId) {
          el.classList.add('active');
        } else {
          el.classList.remove('active');
        }
      }
    });
  }

  // ==========================================
  // TELEMETRY STATE RECONCILIATION
  // ==========================================
  updateTelemetry(data) {
    if (!data) return;

    // Position
    if (data.position) {
      this.dronePos.set(data.position.x, data.position.y, data.position.z);
    }

    // Orientation: Roll, Pitch, Yaw
    if (data.orientation) {
      const pitchRad = THREE.MathUtils.degToRad(data.orientation.pitch || 0);
      const yawRad = THREE.MathUtils.degToRad(data.orientation.yaw || 0);
      const rollRad = THREE.MathUtils.degToRad(data.orientation.roll || 0);
      this.droneRot.set(pitchRad, yawRad, rollRad);
    }

    // Flight Status & Mode
    if (data.flight_status) {
      this.armed = data.flight_status.armed;
      this.motionMode = data.flight_status.motion_mode || data.motion_mode || 'FLIGHT';
      this.groundContact = data.flight_status.ground_contact !== undefined
        ? data.flight_status.ground_contact
        : (this.dronePos.y <= 1.42);
    } else if (data.armed !== undefined) {
      this.armed = data.armed;
      this.motionMode = data.motion_mode || 'FLIGHT';
      this.groundContact = data.ground_contact !== undefined ? data.ground_contact : (this.dronePos.y <= 1.42);
    }

    // Motor RPMs
    if (data.sensors && data.sensors.motors) {
      this.motorRPMs = data.sensors.motors.map(m => m.rpm || 0);
      const avgRpm = this.motorRPMs.reduce((a, b) => a + b, 0) / 4.0;
      this.propSpeed = avgRpm * 0.008;
    }
  }

  setCameraView(mode) {
    this.cameraMode = mode;
    if (mode === 'OVERVIEW' || mode === 'ORBIT') {
      this.orbitControls.enabled = true;
      this.camera.position.set(this.dronePos.x - 7.5, this.dronePos.y + 9.0, this.dronePos.z + 21.0);
      this.orbitControls.target.copy(this.dronePos);
    } else if (mode === 'FOLLOW' || mode === 'CHASE') {
      this.orbitControls.enabled = false;
    } else if (mode === 'CAMERA' || mode === 'FPV') {
      this.orbitControls.enabled = false;
    } else if (mode === 'TOP') {
      this.orbitControls.enabled = true;
      this.camera.position.set(this.dronePos.x, 155, this.dronePos.z);
      this.orbitControls.target.copy(this.dronePos);
    } else {
      this.orbitControls.enabled = true;
    }
  }

  onResize() {
    const w = this.container.clientWidth || window.innerWidth;
    const h = this.container.clientHeight || window.innerHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  animate() {
    requestAnimationFrame(() => this.animate());

    // 1. Smoothly interpolate drone position & orientation
    if (this.droneGroup) {
      const dx = this.dronePos.x - this.prevDronePos.x;
      const dy = this.dronePos.y - this.prevDronePos.y;
      const dz = this.dronePos.z - this.prevDronePos.z;
      const deltaDistH = Math.sqrt(dx * dx + dz * dz);

      // Lerp world translation and heading (yaw)
      this.droneGroup.position.lerp(this.dronePos, 0.22);
      this.droneGroup.rotation.y = THREE.MathUtils.lerp(this.droneGroup.rotation.y, this.droneRot.y, 0.22);

      const isGrounded = (this.droneGroup.position.y <= 1.42) || this.groundContact;

      // 2. Mode-Specific Motion & Decoupled Gimbal Logic
      if (!this.armed) {
        // ----------------------------------------------------
        // DISARMED / EMERGENCY STOP:
        // Motors completely OFF, no propeller spin
        // ----------------------------------------------------
        this.props.forEach(p => {
          p.blurDisc.material.opacity = 0.0;
        });

        // Inner core sits level
        if (this.innerCoreGroup) {
          this.innerCoreGroup.rotation.x = THREE.MathUtils.lerp(this.innerCoreGroup.rotation.x, 0, 0.15);
          this.innerCoreGroup.rotation.z = THREE.MathUtils.lerp(this.innerCoreGroup.rotation.z, 0, 0.15);
        }

        // Outer cage ceases rolling
        if (this.outerCageGroup) {
          this.outerCageGroup.rotation.x = THREE.MathUtils.lerp(this.outerCageGroup.rotation.x, this.cageRollAngle, 0.1);
        }
      } else if (isGrounded && deltaDistH > 0.002) {
        // ----------------------------------------------------
        // GROUND TRAVEL / GROUND ROLLING:
        // Outer cage rotates forward according to distance travelled
        // ----------------------------------------------------
        const yaw = this.droneGroup.rotation.y;
        const localFwd = -(dz * Math.cos(yaw) + dx * Math.sin(yaw));
        const rollDelta = (localFwd / this.cageRadius) * 2.2;
        this.cageRollAngle += rollDelta;

        if (this.outerCageGroup) {
          this.outerCageGroup.rotation.x = this.cageRollAngle;
        }

        // Inner body and camera remain strictly upright & level!
        if (this.innerCoreGroup) {
          this.innerCoreGroup.rotation.x = THREE.MathUtils.lerp(this.innerCoreGroup.rotation.x, 0, 0.25);
          this.innerCoreGroup.rotation.z = THREE.MathUtils.lerp(this.innerCoreGroup.rotation.z, 0, 0.25);
        }

        // Propellers idle softly during ground traction
        const groundPropSpin = 0.08;
        this.props.forEach(p => {
          p.group.rotation.y += groundPropSpin * p.dir;
          p.blurDisc.material.opacity = 0.08;
        });
      } else {
        // ----------------------------------------------------
        // FLIGHT / TAKEOFF / LANDING:
        // Outer cage does NOT roll - smoothly settles to neutral
        // ----------------------------------------------------
        if (this.outerCageGroup) {
          this.outerCageGroup.rotation.x = THREE.MathUtils.lerp(this.outerCageGroup.rotation.x, 0, 0.08);
        }

        // Inner flight body tilts subtly with flight kinematics (pitch & roll banking)
        if (this.innerCoreGroup) {
          const targetPitch = THREE.MathUtils.clamp(this.droneRot.x, -0.35, 0.35);
          const targetRoll = THREE.MathUtils.clamp(this.droneRot.z, -0.35, 0.35);
          this.innerCoreGroup.rotation.x = THREE.MathUtils.lerp(this.innerCoreGroup.rotation.x, targetPitch, 0.18);
          this.innerCoreGroup.rotation.z = THREE.MathUtils.lerp(this.innerCoreGroup.rotation.z, targetRoll, 0.18);
        }

        // Propellers spin rapidly with motion blur
        const spin = Math.max(0.35, this.propSpeed);
        this.props.forEach(p => {
          p.group.rotation.y += spin * p.dir;
          p.blurDisc.material.opacity = Math.min(0.75, spin * 0.45);
        });
      }

      // Rotate locator diamond and rear strobe
      if (this.locatorMarker) {
        this.locatorMarker.rotation.y += 0.025;
      }
      if (this.strobeLed && this.armed) {
        const t = Date.now() * 0.008;
        this.strobeLed.material.color.setHex((Math.sin(t) > 0.6) ? 0x38bdf8 : 0x075985);
      }

      this.prevDronePos.copy(this.dronePos);
    }

    // 2. Animate Gas Plume Particles
    if (this.gasParticles) {
      this.gasParticles.rotation.y += 0.0015;
    }

    // 3. Update Camera Tracking
    if ((this.cameraMode === 'FOLLOW' || this.cameraMode === 'CHASE') && this.droneGroup) {
      // Third-person chase cam following behind and slightly above the drone
      const offset = new THREE.Vector3(0, 2.6, 7.5);
      offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), this.droneGroup.rotation.y);
      const targetCamPos = this.droneGroup.position.clone().add(offset);
      this.camera.position.lerp(targetCamPos, 0.14);
      this.camera.lookAt(this.droneGroup.position.clone().add(new THREE.Vector3(0, 0.3, 0)));
    } else if ((this.cameraMode === 'CAMERA' || this.cameraMode === 'FPV') && this.droneGroup) {
      // First-person cockpit camera view looking forward out through the cage
      const fwdOffset = new THREE.Vector3(0, 0.0, -0.55);
      fwdOffset.applyAxisAngle(new THREE.Vector3(0, 1, 0), this.droneGroup.rotation.y);
      this.camera.position.copy(this.droneGroup.position).add(fwdOffset);

      const lookTarget = new THREE.Vector3(0, -0.2, -25.0);
      lookTarget.applyAxisAngle(new THREE.Vector3(0, 1, 0), this.droneGroup.rotation.y);
      this.camera.lookAt(this.droneGroup.position.clone().add(lookTarget));
    } else if (this.orbitControls && this.orbitControls.enabled) {
      this.orbitControls.update();
    }

    // Rotate station beacons
    if (this.markerGroup) {
      this.markerGroup.children.forEach(b => {
        if (b.children[0]) b.children[0].rotation.y += 0.02;
      });
    }

    this.renderer.render(this.scene, this.camera);
  }
}
