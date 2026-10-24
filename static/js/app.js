// Client console + Three.js hologram + widgets
const elOutput = document.getElementById("output");
const elForm = document.getElementById("form");
const elCmd = document.getElementById("cmd");

// widgets
const elClk = document.getElementById("clk");
const elCPU = document.getElementById("cpu");
const elMEM = document.getElementById("mem");
const elPROCS = document.getElementById("procs");
const elON = document.getElementById("online");
const elLAT = document.getElementById("latency");
const elIP = document.getElementById("ip");
const elHWM = document.getElementById("hw-mode");
const elHWT = document.getElementById("hw-temp");
const elHWL = document.getElementById("hw-led");

function addLine(text, cls="ai") {
  const div = document.createElement("div");
  div.className = "line " + cls;
  div.textContent = text;
  elOutput.appendChild(div);
  elOutput.scrollTop = elOutput.scrollHeight;
  return div;
}

async function send(text) {
  addLine("you> " + text, "user");
  const thinking = addLine("...", "ai thinking");
  try {
    const r = await fetch("/api/handle", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text})
    });
    const j = await r.json();
    thinking.remove();
    addLine(j.reply || "(no reply)");
  } catch (e) {
    thinking.remove();
    addLine("network error: " + e);
  }
}

elForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const t = elCmd.value.trim();
  if (!t) return;
  elCmd.value = "";
  send(t);
});

addLine("SPEKTRA online. Just talk to me, or type 'help' for commands.");
elCmd.focus();

// ---- Widgets ----
function updateClock(ts) {
  const d = ts ? new Date(ts * 1000) : new Date();
  const pad = n => String(n).padStart(2, "0");
  elClk.textContent = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}
setInterval(() => updateClock(), 1000);

async function pollWidgets() {
  try {
    const r = await fetch("/api/widgets");
    const j = await r.json();
    if (j.ok) {
      const d = j.data;
      updateClock(d.clock);
      elCPU.textContent = d.system.cpu;
      elMEM.textContent = d.system.mem;
      elPROCS.textContent = d.system.procs;
      elON.textContent = d.network.online ? "yes" : "no";
      elLAT.textContent = (d.network.latency_ms ?? "n/a") + " ms";
      elIP.textContent = d.network.ip;
      if (d.hardware) {
        elHWM.textContent = d.hardware.mode;
        elHWT.textContent = d.hardware.temp;
        elHWL.textContent = d.hardware.led;
      }
    }
  } catch (e) {
    // ignore
  }
}
setInterval(pollWidgets, 3000);
pollWidgets();

// ---- Three.js hologram head (same as v1) ----
const canvas = document.getElementById("scene");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, 16/9, 0.1, 100);
camera.position.set(0, 0, 6);

// lights
const key = new THREE.PointLight(0x55eaff, 2, 20); key.position.set(4, 4, 6);
const rim = new THREE.PointLight(0x32ffd2, 1.4, 20); rim.position.set(-5, 2, -2);
scene.add(key, rim);

// head wireframe
const headGeom = new THREE.IcosahedronGeometry(2.0, 3);
const wireMat = new THREE.MeshBasicMaterial({ color: 0x61efff, wireframe: true, transparent: true, opacity: 0.5 });
const head = new THREE.Mesh(headGeom, wireMat);
scene.add(head);

// core
const coreGeom = new THREE.SphereGeometry(0.6, 32, 16);
const coreMat = new THREE.MeshBasicMaterial({ color: 0x4df3c2, transparent: true, opacity: 0.6 });
const core = new THREE.Mesh(coreGeom, coreMat);
scene.add(core);

// eyes
const spriteMat = new THREE.SpriteMaterial({ color: 0x97ffff });
const eyeL = new THREE.Sprite(spriteMat.clone());
const eyeR = new THREE.Sprite(spriteMat.clone());
eyeL.scale.set(0.25, 0.25, 1);
eyeR.scale.set(0.25, 0.25, 1);
eyeL.position.set(-0.5, 0.25, 1.1);
eyeR.position.set(0.5, 0.25, 1.1);
scene.add(eyeL, eyeR);

// ring
const ringGeom = new THREE.TorusGeometry(0.8, 0.02, 8, 80);
const ringMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.9 });
const ring = new THREE.Mesh(ringGeom, ringMat);
ring.rotation.x = Math.PI / 2;
ring.position.y = -1.0;
scene.add(ring);

// scan plane
const scanGeom = new THREE.PlaneGeometry(4.2, 4.2, 1, 1);
const scanMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.08 });
const scan = new THREE.Mesh(scanGeom, scanMat);
scan.rotation.x = Math.PI / 2;
scan.position.y = -0.2;
scene.add(scan);

// resize
function resize() {
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
resize();

// parallax
const mouse = { x: 0, y: 0 };
window.addEventListener("pointermove", (e) => {
  const r = canvas.getBoundingClientRect();
  mouse.x = ((e.clientX - r.left) / r.width) * 2 - 1;
  mouse.y = -((e.clientY - r.top) / r.height) * 2 + 1;
});

// animate
let t = 0;
function tick() {
  t += 0.016;
  head.rotation.y += 0.003;
  head.rotation.x = Math.sin(t * 0.3) * 0.05;
  core.scale.setScalar(1 + Math.sin(t * 3) * 0.05 + 0.05);
  core.material.opacity = 0.5 + 0.25 * Math.sin(t * 2);
  eyeL.position.y = 0.25 + Math.sin(t * 2.8) * 0.02;
  eyeR.position.y = 0.25 + Math.cos(t * 2.6) * 0.02;
  const targetRotY = mouse.x * 0.25;
  const targetRotX = mouse.y * 0.15;
  head.rotation.y += (targetRotY - head.rotation.y) * 0.02;
  head.rotation.x += (targetRotX - head.rotation.x) * 0.02;
  ring.rotation.z += 0.01;
  scan.position.y = -0.2 + Math.sin(t * 1.5) * 0.8;
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}
tick();
