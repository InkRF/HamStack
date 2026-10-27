# HamStack role implementation status

This file tracks the repository's detailed implementation boundaries and maturity.
For a higher-level capability overview, see [`../FEATURES.md`](../FEATURES.md).

A role listed here as implemented is deployable code, not a promise of universal hardware
compatibility. Where a reference deployment has been exercised, that is called out
explicitly. See [qa.md](qa.md) for the distinction between repository QA and real-device
validation.

## Implemented or runnable roles

- `common` — baseline packages/directories/timezone/hostname, opt-in device udev rules, plus shared Docker runtime helper.
- `desktop/hamstack-dev` — Debian-family HamStack development environment around an already-provided source tree.
- `desktop/hamstack-controller` — lean Ansible conference-control workstation around an already-provided source tree.
- `desktop/kiosk` — generic Chromium kiosk/autostart/display helper with optional multi-URL tab rotation (X11, xdotool) and an opt-in Raspberry Pi OS X11 switch.
- `desktop/chirp` — CHIRP-next wheel/pipx workstation install + serial access.
- `desktop/netlogger` — operator-supplied NetLogger Debian package install.
- `digital/fldigi` — Debian package install + optional desktop autostart.
- `digital/flrig` — Debian package install + optional desktop autostart.
- `digital/wsjtx` — Debian package install + optional desktop autostart.
- `digital/multimon-ng` — Debian decoder install + configurable POCSAG/general decoder wrapper/service.
- `digital/unipager` — upstream Debian UniPager install with transmit controller stopped by default.
- `digital/js8call` — current upstream x86-64/ARM64 AppImage install + desktop integration.
- `digital/ft8web` — transactional local mirror of OK1CDJ FT8Web behind HTTPS.
- `infrastructure/technitium-dns` — official Technitium DNS container, persistent state, secure bootstrap, forwarding, optional local primary zone.
- `infrastructure/netboot` — minimal HTTP/iPXE content/menu service; no DHCP/TFTP yet.
- `network/44connect` — 44Net Connect WireGuard client; split tunnel to 44Net prefixes by default.
- `network/openwrt` — rudimentary OpenWrt/GL.iNet UCI backend for hostname, LAN/DHCP, Wi-Fi, routes, DNS, and simple firewall zones.
- `network/routeros` — rudimentary RouterOS API backend for identity, IP addresses, routes, DNS, plus native structured API-path escape hatches.
- `network/aredn` — read-only polling/integration for existing AREDN nodes via the documented sysinfo API.
- `packet/aprs` — Graywolf APRS profile: station identity, iGate, digipeater, simulation settings. Beacon/rule CRUD remains guarded.
- `packet/enigma-bbs` — IP-only Docker deployment with Telnet, SSH, and WSS through Caddy; RF/KISS shim planned.
- `packet/graywolf` — official release install + API-managed station/audio/channel/PTT/KISS/AGWPE configuration.
- `packet/linbpq` — generic LinBPQ node/BBS config + service model; binary source is operator supplied.
- `packet/winlink` — Pat install/config/web service with operator-selected Winlink transports.
- `services/blur-deck` — ReadyMedia/MiniDLNA media directory for Roku/DLNA conference displays.
- `services/cloudlog` — native Apache/PHP/MariaDB local Cloudlog deployment; upstream web setup remains operator-owned.
- `services/conham-display` — transactional last-known-good local mirror of conham.radio behind HTTPS.
- `services/dcdash` — DCDash Python/Gunicorn/systemd deployment with native TLS and health verification; source repo is operator supplied.
- `services/gatus` — containerized Gatus status page behind HTTPS with HamStack-derived and operator-defined checks.
- `services/gps-time` — gpsd + chrony GNSS/PPS reference with opt-in LAN NTP service.
- `services/meshtastic-dashboard` — official Meshtastic Web container behind HTTPS.
- `services/wavelog` — upstream-recommended Wavelog + MariaDB containers behind HTTPS; normal web installer remains upstream-managed.
- `visual/gridtracker` — latest/pinned GridTracker2 Debian install on amd64/arm64 + optional desktop autostart.
- `visual/openhamclock` — official container behind Caddy internal-CA HTTPS; plaintext app port remains container-private.
- `visual/openwebrx` — OpenWebRX container behind Caddy internal-CA HTTPS; explicit SDR device mapping.
- `digital/selfie_station` — headless Picamera2/PySSTV/AIOC service with TX disabled by default.
- `digital/slowrxd` — headless slowrxd SSTV receive daemon built from a pinned upstream commit, with an optional event hook.
- `digital/sstv_booth` — FastAPI kiosk booth: slowrxd image display plus pedal-triggered Picamera2 selfie SSTV transmit with cooldown, hourly cap, and RX-busy guardrails; TX disabled by default.
- `digital/morse-keyer` — HamRadioVillage morse-keyer GPIO-to-virtual-keyboard bridge (straight or iambic) bundled in the role, with X11 auto-repeat turned off for the key.
- `digital/sstv-rx` — GQRX + HamRadioVillage QSSTV receive appliance with managed Pulse/PipeWire-Pulse audio routing; exercised on the HRV reference receive appliance.
- `digital/sstv-workstation` — general-purpose HRV QSSTV desktop workstation; detailed per-user audio/PTT preferences remain operator-managed.
- `voice/allstar` — ASL3 node/radio/HTTP-registration configuration on a preinstalled upstream system; exercised on HRV reference hardware, with audio/radio calibration remaining site-specific.
- `voice/wpsd` — WPSD identity/modem/frequency/mode configuration on a pre-imaged upstream appliance; exercised on HRV reference hardware, while provider/account workflows remain upstream-managed.

## Still partial by design

- `desktop/kiosk` does not configure desktop-manager autologin.
- `desktop/netlogger` cannot fetch through NetLogger's interactive public download form; the operator supplies a `.deb` or authorized URL.
- `digital/ft8web` mirrors the deployed site rather than consuming a formal upstream self-host artifact.
- `digital/unipager` installs/configures service lifecycle but leaves pager RF/network/hardware settings to UniPager.
- `infrastructure/technitium-dns` does not automate DHCP, split-horizon apps/views, or complete DNS record management.
- `infrastructure/netboot` deliberately omits DHCP, proxy-DHCP, and TFTP; its supported scope is HTTP/iPXE content.
- `network/openwrt` does not discover/redesign switch/DSA topology, multi-WAN, or GL.iNet vendor UI behavior.
- `network/routeros` translates only a small safe common subset; DHCP/Wi-Fi/firewall can use native-path data until broader cross-version modeling is validated.
- `network/aredn` is monitoring-only; HamStack does not own AREDN firmware or RF/mesh configuration.
- `packet/aprs` does not yet create/update beacons or digi rules automatically.
- `packet/enigma-bbs` has no Graywolf KISS/AX.25 transport shim yet.
- `packet/linbpq` does not redistribute LinBPQ or automatically select an upstream binary.
- `packet/winlink` exposes Pat transports but does not automatically deploy every modem/rig stack.
- `services/cloudlog` and `services/wavelog` intentionally leave application setup/logging workflow to their upstream products.
- `services/conham-display` mirrors rendered HTML today; Markdown-native building and Roku-specific rendering can come later.
- `visual/openwebrx` does not yet create an admin account or receiver profiles.

## Deployment profiles

Thin profiles are provided for:

- HamCube / central service-display node;
- conference control station;
- development workstation.

See [profiles.md](profiles.md).

## Design rule

A role that cannot safely own a workflow should stop at a clear upstream/operator
boundary rather than silently pretending to manage it. Disabled roles remain inert.
