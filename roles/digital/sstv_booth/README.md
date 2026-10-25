# `sstv_booth` role

> **Status:** implemented interactive SSTV receive display and pedal-triggered selfie transmitter; TX remains disabled by default.

## Purpose

Run an event-booth SSTV station on one Raspberry Pi: a kiosk page shows
images received by `digital/slowrxd`, and a visitor can step on a foot pedal to
have their photo taken and sent over the air as SSTV.

## Expected starting state

- Raspberry Pi OS (Debian-family) with a Picamera2-supported camera (the
  reference build uses a Camera Module 3), a USB foot pedal, and an AIOC
  (All-In-One Cable) connected to the radio.
- `digital/slowrxd` writing received images to `hamstack_sstv_booth_rx_dir`
  and posting hook events to this booth.
- `desktop/kiosk` (or any browser) showing `http://127.0.0.1:<port>/`.

## Booth flow

| Mode | What the screen shows | Pedal |
| --- | --- | --- |
| STANDBY | Latest received image; while receiving, the in-progress decode (refreshed about every second, as fast as slowrxd rewrites it, which is at most every 5 s); a strip of the last 8 RX/TX images. | Starts a selfie unless a guardrail blocks it. |
| COUNTDOWN | 5 s countdown over the live, mirrored camera preview (MJPEG). | Ignored. |
| REVIEW | The captured image with the callsign overlay for 3 s. SSTV audio is encoded in the background. | Cancels and returns to STANDBY. |
| TX | The image and a progress bar for the length of the transmission. | Ignored. |

The overlay always includes the callsign. `hamstack_sstv_booth_blurb_mode`
adds a top line: `fixed` (`blurb_text`), `random` (one of `blurb_list` per
image), or `none`.

## Transmit safety

- **RF transmission is disabled by default.** With
  `hamstack_sstv_booth_tx_enabled: false`, the booth runs the full flow as a
  dry run: no PTT, no audio, and a "TX DISABLED" badge on screen. Enabling TX
  requires a real callsign.
- `tx_cooldown_s` (default 60) and `max_tx_per_hour` (default 20, sliding
  window persisted in `data_dir/tx_log.json`) apply to every selfie, including
  dry runs, so the booth behaves the same before and after TX is enabled.
- The pedal is refused while an image is being received, so the booth does not
  transmit over another station.
- Receive hook events are ignored during the booth's own transmission and for
  `rx_ignore_tail_s` afterwards.
- PTT is released in a `finally` block, and SIGTERM stops playback and releases
  PTT before the web server shuts down.

Validate the AIOC device, PTT behaviour, radio audio level, and a dry run before
setting `hamstack_sstv_booth_tx_enabled: true`. Frequencies and radio settings
are operator-owned.

## Implementation

The application is a FastAPI service (`files/sstv_booth`) running as the
unprivileged `hamstack-sstv-booth` account and listening on
`hamstack_sstv_booth_listen_address` (default `127.0.0.1`) only. Its image,
CW-ID, AIOC PTT, and playback code is copied from
[`selfie_station`](../selfie_station/README.md) and parameterised.

HamStack renders `/etc/hamstack/sstv_booth.json` and
`/etc/systemd/system/hamstack-sstv-booth.service` authoritatively and installs
the application under `hamstack_sstv_booth_install_dir`. Images and TX history
live under `hamstack_sstv_booth_data_dir`.

Endpoints: `/` (kiosk page), `/api/events` (SSE state), `/api/state`,
`/api/gallery`, `POST /api/pedal`, `POST /api/rx-event` (slowrxd hook),
`/stream.mjpg` (camera preview).

## Development mode

Without camera, pedal, or radio hardware:

```bash
cd roles/digital/sstv_booth/files
python3 -m sstv_booth --dev
```

`--dev` uses a synthetic camera, skips the pedal device, makes the Space bar in
the page act as the pedal, and stores data under the system temp directory.
TX stays disabled unless a config file enables it. Offline tests:

```bash
cd roles/digital/sstv_booth/files
python3 -m unittest discover -s tests
```

`scripts/sstv-loopback-test.sh` checks the receive path on a deployed booth
with `snd-aloop`, and `scripts/sstv-booth-install.sh` installs the booth and
slowrxd without Ansible.

## Configuration

See the [HamStack configuration reference](../../../docs/configuration.md#role-sstv-booth)
for the public variables owned by this role.
