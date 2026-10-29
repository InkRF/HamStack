#!/usr/bin/env bash
# Install the HamStack SSTV booth (digital/slowrxd + digital/sstv_booth)
# directly on a Raspberry Pi without Ansible.
#
# This is a field fallback. The Ansible roles remain the reference
# implementation; keep the units and paths below consistent with
# roles/digital/slowrxd and roles/digital/sstv_booth.
#
# Usage (from a HamStack checkout on the Pi):
#   sudo scripts/sstv-booth-install.sh --callsign N0CALL [options]
#
# Options:
#   --callsign CALL      Station callsign (required)
#   --port PORT          Booth HTTP port on 127.0.0.1 (default 8080)
#   --device PCM         ALSA playback device for TX (default plughw:CARD=AllInOneCable,DEV=0)
#   --rx-card NAME       ALSA card name slowrxd captures from (default All-In-One-Cable)
#   --pedal PATH         Foot-pedal input device (default PCsensor by-id path)
#   --blurb TEXT         Fixed top-of-image text (default none)
#   --kiosk-user USER    Desktop user that gets a Chromium kiosk autostart entry
#   --tx-enabled         Allow the booth to key the radio (default: dry run only)
set -euo pipefail

SLOWRX_REPO=https://github.com/sjlongland/slowrx.git
SLOWRX_COMMIT=c94327ae40ab970b0bea20ebb378d71f8e69b98a
SLOWRX_SRC=/opt/hamstack/slowrx-source
SLOWRXD_BIN=/usr/local/bin/slowrxd
SLOWRXD_HOOK=/usr/local/libexec/hamstack/slowrxd-hook
SLOWRXD_USER=hamstack-slowrxd
RX_DIR=/var/lib/hamstack/slowrxd

BOOTH_USER=hamstack-sstv-booth
BOOTH_INSTALL=/opt/hamstack/sstv_booth
BOOTH_VENV=$BOOTH_INSTALL/venv
BOOTH_DATA=/var/lib/hamstack/sstv_booth
BOOTH_CONFIG=/etc/hamstack/sstv_booth.json

CALLSIGN=""
PORT=8080
DEVICE="plughw:CARD=AllInOneCable,DEV=0"
RX_CARD=All-In-One-Cable
PEDAL=/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd
BLURB=""
KIOSK_USER=""
TX_ENABLED=false

usage() {
  sed -n '2,21p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --callsign) CALLSIGN="${2:?}"; shift 2 ;;
    --port) PORT="${2:?}"; shift 2 ;;
    --device) DEVICE="${2:?}"; shift 2 ;;
    --rx-card) RX_CARD="${2:?}"; shift 2 ;;
    --pedal) PEDAL="${2:?}"; shift 2 ;;
    --blurb) BLURB="${2:?}"; shift 2 ;;
    --kiosk-user) KIOSK_USER="${2:?}"; shift 2 ;;
    --tx-enabled) TX_ENABLED=true; shift ;;
    -h|--help) usage 0 ;;
    *) echo "Unknown option: $1" >&2; usage 1 ;;
  esac
done

[ "$(id -u)" -eq 0 ] || { echo "Run as root (sudo)." >&2; exit 1; }
[ -n "$CALLSIGN" ] || { echo "--callsign is required." >&2; exit 1; }
case "$PORT" in ''|*[!0-9]*) echo "--port must be a number." >&2; exit 1 ;; esac

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_SRC="$REPO_ROOT/roles/digital/sstv_booth/files/sstv_booth"
[ -d "$APP_SRC" ] || { echo "Cannot find $APP_SRC; run from a HamStack checkout." >&2; exit 1; }

echo "==> Installing packages"
apt-get update
apt-get install -y \
  alsa-utils build-essential curl fonts-dejavu-core git libasound2-dev \
  libfftw3-dev libgd-dev pkg-config python3-evdev python3-fastapi \
  python3-picamera2 python3-pil python3-pip python3-serial python3-uvicorn \
  python3-venv

echo "==> Creating service accounts"
ensure_user() {
  local user="$1" home="$2" groups="$3"
  getent group "$user" >/dev/null || groupadd --system "$user"
  if ! getent passwd "$user" >/dev/null; then
    useradd --system --gid "$user" --home-dir "$home" --no-create-home \
      --shell /usr/sbin/nologin "$user"
  fi
  usermod -a -G "$groups" "$user"
}
ensure_user "$SLOWRXD_USER" "$RX_DIR" audio
ensure_user "$BOOTH_USER" "$BOOTH_DATA" audio,dialout,video,input

echo "==> Building slowrxd at $SLOWRX_COMMIT"
if [ ! -d "$SLOWRX_SRC/.git" ]; then
  git clone "$SLOWRX_REPO" "$SLOWRX_SRC"
fi
git -C "$SLOWRX_SRC" fetch --quiet origin
git -C "$SLOWRX_SRC" checkout --quiet --force "$SLOWRX_COMMIT"
if [ ! -e "$SLOWRX_SRC/.hamstack-built-$SLOWRX_COMMIT" ]; then
  (
    cd "$SLOWRX_SRC"
    rm -f .hamstack-built-*
    make clean
    make slowrxd
    touch ".hamstack-built-$SLOWRX_COMMIT"
  )
fi
install -o root -g root -m 0755 "$SLOWRX_SRC/slowrxd" "$SLOWRXD_BIN"

echo "==> Configuring slowrxd"
install -d -o "$SLOWRXD_USER" -g "$SLOWRXD_USER" -m 0755 "$RX_DIR"
install -d -o root -g root -m 0755 "$(dirname "$SLOWRXD_HOOK")"
cat > "$SLOWRXD_HOOK" <<EOF
#!/bin/sh
# Installed by scripts/sstv-booth-install.sh. See roles/digital/slowrxd.
event="\${1:-}"
image="\$(basename -- "\${2:-}")"
case "\$event" in
  VIS_DETECT|IMAGE_REFRESHED|RECEIVE_END) ;;
  *) exit 0 ;;
esac
case "\$image" in
  *[!A-Za-z0-9._-]*) image="" ;;
esac
curl -fsS -m 3 -o /dev/null \\
  -H 'Content-Type: application/json' \\
  -d "{\\"event\\":\\"\${event}\\",\\"image\\":\\"\${image}\\"}" \\
  'http://127.0.0.1:$PORT/api/rx-event' >/dev/null 2>&1 &
exit 0
EOF
chmod 0755 "$SLOWRXD_HOOK"

cat > /etc/tmpfiles.d/hamstack-slowrxd.conf <<EOF
e $RX_DIR/*.au - - - 1d
EOF

cat > /etc/default/hamstack-slowrxd <<EOF
SLOWRXD_OUTPUT_DIR=$RX_DIR
SLOWRXD_DEVICE=$RX_CARD
SLOWRXD_SAMPLE_RATE=48000
SLOWRXD_CHANNEL=l
SLOWRXD_HOOK_ARGS="-x $SLOWRXD_HOOK"
SLOWRXD_EXTRA_ARGS=""
EOF

cat > /etc/systemd/system/hamstack-slowrxd.service <<EOF
[Unit]
Description=HamStack slowrxd SSTV receive daemon
After=network.target sound.target

[Service]
Type=simple
User=$SLOWRXD_USER
Group=$SLOWRXD_USER
SupplementaryGroups=audio
EnvironmentFile=/etc/default/hamstack-slowrxd
WorkingDirectory=$RX_DIR
ExecStart=$SLOWRXD_BIN -d \${SLOWRXD_OUTPUT_DIR} -p \${SLOWRXD_DEVICE} -r \${SLOWRXD_SAMPLE_RATE} -c \${SLOWRXD_CHANNEL} \$SLOWRXD_HOOK_ARGS \$SLOWRXD_EXTRA_ARGS
Restart=always
RestartSec=5
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
ReadWritePaths=$RX_DIR

[Install]
WantedBy=multi-user.target
EOF

echo "==> Installing SSTV booth application"
install -d -o root -g root -m 0755 "$BOOTH_INSTALL" /etc/hamstack
rm -rf "$BOOTH_INSTALL/sstv_booth"
cp -r "$APP_SRC" "$BOOTH_INSTALL/sstv_booth"
find "$BOOTH_INSTALL/sstv_booth" -name __pycache__ -prune -exec rm -rf {} +
chown -R root:root "$BOOTH_INSTALL/sstv_booth"
chmod -R u=rwX,go=rX "$BOOTH_INSTALL/sstv_booth"
[ -x "$BOOTH_VENV/bin/python3" ] || python3 -m venv --system-site-packages "$BOOTH_VENV"
"$BOOTH_VENV/bin/pip" install --quiet pysstv

for dir in "$BOOTH_DATA" "$BOOTH_DATA/gallery" "$BOOTH_DATA/work"; do
  install -d -o "$BOOTH_USER" -g "$BOOTH_USER" -m 0755 "$dir"
done

CALLSIGN="$CALLSIGN" PORT="$PORT" DEVICE="$DEVICE" PEDAL="$PEDAL" BLURB="$BLURB" \
TX_ENABLED="$TX_ENABLED" RX_DIR="$RX_DIR" BOOTH_DATA="$BOOTH_DATA" \
python3 - > "$BOOTH_CONFIG" <<'EOF'
import json
import os

print(json.dumps({
    "callsign": os.environ["CALLSIGN"],
    "listen_address": "127.0.0.1",
    "http_port": int(os.environ["PORT"]),
    "data_dir": os.environ["BOOTH_DATA"],
    "rx_dir": os.environ["RX_DIR"],
    "blurb_mode": "fixed" if os.environ["BLURB"] else "none",
    "blurb_text": os.environ["BLURB"],
    "tx_enabled": os.environ["TX_ENABLED"] == "true",
    "aioc_audio_device": os.environ["DEVICE"],
    "pedal_device": os.environ["PEDAL"],
}, indent=2))
EOF
chmod 0644 "$BOOTH_CONFIG"

cat > /etc/systemd/system/hamstack-sstv-booth.service <<EOF
[Unit]
Description=HamStack SSTV booth (kiosk app, selfie SSTV transmitter)
After=network.target sound.target

[Service]
Type=simple
User=$BOOTH_USER
Group=$BOOTH_USER
SupplementaryGroups=audio dialout video input
WorkingDirectory=$BOOTH_DATA
Environment=PYTHONPATH=$BOOTH_INSTALL
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=$BOOTH_VENV/bin/python3 -m sstv_booth --config $BOOTH_CONFIG
Restart=on-failure
RestartSec=3
TimeoutStopSec=15
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
ReadWritePaths=$BOOTH_DATA

[Install]
WantedBy=multi-user.target
EOF

if [ -n "$KIOSK_USER" ]; then
  echo "==> Adding Chromium kiosk autostart for $KIOSK_USER"
  apt-get install -y chromium unclutter x11-xserver-utils || apt-get install -y chromium-browser unclutter x11-xserver-utils
  home="$(getent passwd "$KIOSK_USER" | cut -d: -f6)"
  browser="$(command -v chromium || command -v chromium-browser)"
  install -d -o "$KIOSK_USER" -m 0755 "$home/.config/autostart"
  cat > "$home/.config/autostart/hamstack-sstv-booth-kiosk.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=HamStack SSTV booth kiosk
Exec=sh -c 'xset s off; xset s noblank; xset -dpms; unclutter -idle 0.5 -root & exec $browser --kiosk --no-first-run --disable-session-crashed-bubble --disable-infobars http://127.0.0.1:$PORT/'
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
  chown "$KIOSK_USER" "$home/.config/autostart/hamstack-sstv-booth-kiosk.desktop"
fi

echo "==> Starting services"
systemd-tmpfiles --create /etc/tmpfiles.d/hamstack-slowrxd.conf
systemctl daemon-reload
systemctl enable hamstack-slowrxd hamstack-sstv-booth
systemctl restart hamstack-slowrxd hamstack-sstv-booth

echo
echo "SSTV booth installed: http://127.0.0.1:$PORT/  (TX enabled: $TX_ENABLED)"
echo "Logs: journalctl -u hamstack-sstv-booth -u hamstack-slowrxd -f"
