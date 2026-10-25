"use strict";

const $ = (id) => document.getElementById(id);
let state = null;
let clockOffset = 0;
let rxTimer = null;
let lastStripKey = "";

function show(el, visible) {
  el.classList.toggle("hidden", !visible);
}

// Swap an <img> only after the new frame loads, so a missing or half-written
// in-progress image never flashes a broken picture.
function swapImage(img, url) {
  const next = new Image();
  next.onload = () => { img.src = url; };
  next.src = url;
}

function refreshInprogress() {
  swapImage($("main-image"), "/rx/inprogress.png?t=" + Date.now());
}

function renderStrip(items) {
  const key = items.map((i) => i.name).join(",");
  if (key === lastStripKey) return;
  lastStripKey = key;
  $("strip").replaceChildren(...items.map((item) => {
    const div = document.createElement("div");
    div.className = "thumb " + item.kind;
    const img = document.createElement("img");
    img.src = item.url;
    const label = document.createElement("span");
    label.textContent = item.kind.toUpperCase();
    div.append(img, label);
    return div;
  }));
}

function renderStatus() {
  if (!state) return;
  const now = Date.now() / 1000 + clockOffset;
  const cooldown = Math.ceil(state.cooldown_until - now);
  let text = `${state.tx_last_hour}/${state.max_tx_per_hour} this hour`;
  if (cooldown > 0) text = `Next selfie in ${cooldown} s · ` + text;
  $("status").textContent = text;
}

function render(s) {
  const prev = state;
  state = s;
  clockOffset = s.server_time - Date.now() / 1000;

  $("callsign").textContent = s.callsign;
  $("sstv-mode").textContent = "SSTV " + s.sstv_mode + (s.dev ? " · DEV" : "");
  const badge = $("tx-badge");
  badge.textContent = s.tx_enabled ? "TX ENABLED" : "TX DISABLED";
  badge.classList.toggle("enabled", s.tx_enabled);

  const mode = s.mode;
  const standby = mode === "standby";
  $("stage").dataset.mode = mode;

  // Live preview only while counting down; dropping src closes the stream.
  const preview = $("preview");
  if (mode === "countdown") {
    if (!preview.getAttribute("src")) preview.src = "/stream.mjpg";
    show(preview, true);
  } else {
    show(preview, false);
    preview.removeAttribute("src");
  }

  show($("countdown"), mode === "countdown" && s.countdown > 0);
  $("countdown").textContent = s.countdown || "";

  const review = $("review");
  const reviewing = (mode === "review" || mode === "tx") && Boolean(s.review_url);
  if (reviewing && (!prev || prev.review_url !== s.review_url)) review.src = s.review_url;
  show(review, reviewing);

  const banner = $("banner");
  banner.classList.remove("is-rx", "is-review");
  if (mode === "review") {
    banner.textContent = "Looking good? Press the pedal to cancel";
    banner.classList.add("is-review");
    show(banner, true);
  } else if (standby && s.receiving) {
    banner.textContent = "Receiving " + (s.rx_mode || "SSTV") + "…";
    banner.classList.add("is-rx");
    show(banner, true);
  } else {
    show(banner, false);
  }

  // Main image: the in-progress decode while receiving, else the latest RX.
  const main = $("main-image");
  if (s.receiving) {
    if (!rxTimer) {
      refreshInprogress();
      rxTimer = setInterval(refreshInprogress, 1000);
    } else if (prev && prev.rx_version !== s.rx_version) {
      refreshInprogress();
    }
  } else {
    if (rxTimer) { clearInterval(rxTimer); rxTimer = null; }
    const changed = !prev || prev.receiving || !prev.latest_rx || !s.latest_rx
      || prev.latest_rx.name !== s.latest_rx.name;
    if (s.latest_rx && changed) swapImage(main, s.latest_rx.url);
  }
  const hasMain = s.receiving || Boolean(s.latest_rx);
  show(main, standby && hasMain);
  show($("placeholder"), standby && !hasMain);
  show($("prompt"), standby && !s.receiving);

  const bar = $("txbar");
  show(bar, mode === "tx");
  bar.classList.toggle("dry", !s.tx_enabled);
  $("txbar-fill").style.width = Math.round(s.tx_progress * 100) + "%";
  const remaining = Math.max(0, Math.ceil(s.tx_duration * (1 - s.tx_progress)));
  $("txbar-label").textContent =
    (s.tx_enabled ? "Transmitting" : "Dry run (TX disabled)") + ` · ${remaining} s`;

  $("toast").textContent = s.toast || "";
  show($("toast"), Boolean(s.toast));

  renderStrip(s.gallery);
  renderStatus();
}

function connect() {
  const source = new EventSource("/api/events");
  source.onmessage = (event) => render(JSON.parse(event.data));
  source.onerror = () => {
    source.close();
    setTimeout(connect, 2000);
  };
}

// --dev: the Space bar stands in for the foot pedal.
document.addEventListener("keydown", (event) => {
  if (!state || !state.dev || event.code !== "Space" || event.repeat) return;
  event.preventDefault();
  fetch("/api/pedal", { method: "POST" });
});

// Toasts expire server-side; re-read state so they clear without a new event.
setInterval(() => {
  renderStatus();
  if (state && state.toast && Date.now() / 1000 + clockOffset > state.server_time + 4.2) {
    fetch("/api/state").then((r) => r.json()).then(render).catch(() => {});
  }
}, 1000);

for (const id of ["preview", "review", "countdown", "banner", "txbar", "toast", "main-image"]) {
  show($(id), false);
}
connect();
