#!/usr/bin/env bash
# End-to-end receive-path test for a deployed SSTV booth, without RF.
#
# Plays a generated SSTV test transmission into an snd-aloop loopback card,
# decodes it with slowrxd (same output directory and hook as the service),
# and checks that the image reaches the booth gallery.
#
#   sudo scripts/sstv-loopback-test.sh [--timeout SECONDS] [--mode Robot36]
#
# hamstack-slowrxd is stopped for the duration of the test and restarted
# afterwards, even on failure. Nothing is transmitted on the radio.
set -euo pipefail

TIMEOUT=60
MODE=Robot36
while [ $# -gt 0 ]; do
  case "$1" in
    --timeout) TIMEOUT="${2:?}"; shift 2 ;;
    --mode) MODE="${2:?}"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

[ "$(id -u)" -eq 0 ] || { echo "Run as root (sudo)." >&2; exit 1; }

ENV_FILE=/etc/default/hamstack-slowrxd
BOOTH_CONFIG=/etc/hamstack/sstv_booth.json
SLOWRXD_BIN=/usr/local/bin/slowrxd
BOOTH_INSTALL=/opt/hamstack/sstv_booth
TEST_UNIT=hamstack-slowrxd-loopback
LOOP_PLAY="plughw:CARD=Loopback,DEV=0,SUBDEV=0"
LOOP_CAPTURE="plughw:CARD=Loopback,DEV=1,SUBDEV=0"

for path in "$ENV_FILE" "$BOOTH_CONFIG" "$SLOWRXD_BIN" "$BOOTH_INSTALL/venv/bin/python3"; do
  [ -e "$path" ] || { echo "FAIL: $path not found; deploy slowrxd and sstv_booth first." >&2; exit 1; }
done

# shellcheck disable=SC1090
. "$ENV_FILE"
SLOWRXD_USER="$(systemctl show -p User --value hamstack-slowrxd)"
BOOTH_URL="$(python3 -c 'import json,sys; c=json.load(open(sys.argv[1])); print(f"http://127.0.0.1:{c[\"http_port\"]}")' "$BOOTH_CONFIG")"

gallery_rx_names() {
  curl -fsS -m 5 "$BOOTH_URL/api/gallery?limit=200" \
    | python3 -c 'import json,sys; print("\n".join(i["name"] for i in json.load(sys.stdin) if i["kind"] == "rx"))'
}

echo "==> Checking booth at $BOOTH_URL"
before="$(gallery_rx_names)" || { echo "FAIL: booth API not reachable at $BOOTH_URL" >&2; exit 1; }

echo "==> Loading snd-aloop"
modprobe snd-aloop
aplay -l | grep -q Loopback || { echo "FAIL: Loopback card did not appear" >&2; exit 1; }

WORK="$(mktemp -d)"
restore() {
  systemctl stop "$TEST_UNIT" >/dev/null 2>&1 || true
  systemctl reset-failed "$TEST_UNIT" >/dev/null 2>&1 || true
  systemctl start hamstack-slowrxd || true
  rm -rf "$WORK"
}
trap restore EXIT

echo "==> Generating $MODE test WAV"
PYTHONPATH="$BOOTH_INSTALL" "$BOOTH_INSTALL/venv/bin/python3" -m sstv_booth.tx \
  --test-wav "$WORK/test.wav" --mode "$MODE" --callsign TEST
chmod 0644 "$WORK/test.wav"

echo "==> Running slowrxd on the loopback capture device"
systemctl stop hamstack-slowrxd
marker="$WORK/marker"
touch "$marker"
# shellcheck disable=SC2086
systemd-run --quiet --unit="$TEST_UNIT" \
  --uid="$SLOWRXD_USER" --gid="$SLOWRXD_USER" -p SupplementaryGroups=audio \
  -p WorkingDirectory="$SLOWRXD_OUTPUT_DIR" \
  "$SLOWRXD_BIN" -d "$SLOWRXD_OUTPUT_DIR" -p "$LOOP_CAPTURE" \
  -r "$SLOWRXD_SAMPLE_RATE" -c "$SLOWRXD_CHANNEL" $SLOWRXD_HOOK_ARGS
sleep 2
systemctl is-active --quiet "$TEST_UNIT" || {
  journalctl -u "$TEST_UNIT" --no-pager -n 20 >&2
  echo "FAIL: slowrxd did not start on $LOOP_CAPTURE" >&2
  exit 1
}

echo "==> Playing test transmission into the loopback"
aplay -q -D "$LOOP_PLAY" "$WORK/test.wav"

echo "==> Waiting up to ${TIMEOUT}s for the decoded image"
deadline=$((SECONDS + TIMEOUT))
image=""
new_rx=""
while [ $SECONDS -lt $deadline ]; do
  image="$(find "$SLOWRXD_OUTPUT_DIR" -maxdepth 1 -name '*.png' ! -name 'inprogress.png' \
    ! -name 'latest.png' -newer "$marker" -print -quit)"
  if [ -n "$image" ]; then
    new_rx="$(comm -13 <(printf '%s\n' "$before" | sort) <(gallery_rx_names | sort) | head -n 1)"
    [ -n "$new_rx" ] && break
  fi
  sleep 2
done

if [ -z "$image" ]; then
  journalctl -u "$TEST_UNIT" --no-pager -n 30 >&2
  echo "FAIL: slowrxd produced no final image" >&2
  exit 1
fi
echo "    slowrxd image: $image"
if [ -z "$new_rx" ]; then
  echo "FAIL: image decoded but did not reach the booth gallery (check the hook URL and booth logs)" >&2
  exit 1
fi
echo "    booth gallery: $new_rx"
echo "PASS: loopback SSTV reached the booth gallery"
