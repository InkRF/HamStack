# Changelog

All notable public HamStack releases are recorded here.

HamStack uses semantic versioning while the public interface is still evolving. During
the `0.x` line, role variables and implementation boundaries may change between minor
releases when needed to establish a durable public contract.

## [Unreleased]

### Added

- `digital/slowrxd`: builds the upstream `slowrx-daemon` branch at a pinned commit
  and runs `slowrxd` as a sandboxed receive-only service with an event hook.
- `digital/sstv_booth`: interactive SSTV booth with a local kiosk page (SSE
  state, MJPEG camera preview, RX gallery) and pedal-triggered selfie SSTV
  transmission. TX is disabled by default and guarded by a cooldown, an hourly
  cap, and an RX-busy check.
- `playbooks/profiles/sstv-booth.yml`, `scripts/sstv-booth-install.sh`
  (no-Ansible fallback), and `scripts/sstv-loopback-test.sh` (snd-aloop
  receive-path test).
- `digital/morse-keyer`: deploys the HamRadioVillage morse-keyer bridge
  (bundled with permission), so a Morse key, paddles, or keyer output on Raspberry Pi GPIO
  presses Space for browser trainers such as hamvillage.org/morse-trainer.
- `desktop/kiosk`: optional multi-URL tabs with idle-aware `xdotool` tab
  rotation, and an opt-in Raspberry Pi OS X11 session switch.
- `common`: opt-in `/etc/udev/rules.d/90-hamstack-devices.rules` generated
  from `hamstack_devices` (for example a stable `/dev/aioc-ptt` symlink).
- `playbooks/profiles/aprs-kiosk.yml`: receive-only Graywolf APRS kiosk
  profile with an optional CW practice day mode.

### Security

- `packet/winlink`: the Pat package is downloaded into the root-owned HamStack
  package cache and verified against per-architecture SHA-256 digests instead of
  being installed from an unverified file in `/tmp`.
- `services/cloudlog`: `application/config` (database credentials) is no longer
  made world-readable on every run.
- `digital/multimon-ng`: the managed decoder service runs as a dedicated
  unprivileged account under a sandboxed systemd unit instead of root.
- `digital/selfie_station`: the service runs as the dedicated `hamstack-selfie`
  account under a sandboxed systemd unit with a root-owned install tree instead
  of the Ansible automation account.
- Download verification: JS8Call AppImages ship with upstream digests and are
  verified by default; GridTracker2, Graywolf, CHIRP (wheel), NetLogger, and
  LinBPQ accept `sha256:` checksums, and all download URLs must use HTTPS.
  GridTracker2 caches packages by upstream filename so version changes are
  honored.
- `network/openwrt`: Wi-Fi, radio, route, and firewall-zone identifiers are
  validated before being rendered into the UCI script executed on the router.
- `network/routeros`: `hamstack_routeros_api_validate_certs` now defaults to
  `true`; `playbooks/network.yml` no longer inherits `become`.
- `infrastructure/technitium-dns`: the admin password must be at least 12
  characters.
- `voice/allstar` and `voice/wpsd`: credential-bearing files no longer leave
  Ansible backup copies by default (`hamstack_wpsd_config_backups`), and WPSD
  pass-through settings are written with `no_log`.

### Fixed

- `digital/ft8web`: added the missing nginx template that prevented the role
  from deploying.
- `scripts/qa.py` now fails when a role task references a template or file the
  role does not ship.
- Repository CI now passes `yamllint` and `ansible-lint`: a list-indentation
  error in `roles/common/defaults/main.yml` is fixed, tasks that set
  `become_user` declare `become` explicitly, and `.ansible-lint` downgrades the
  `var-naming[no-role-prefix]` and `yaml[line-length]` rules to warnings
  because the `hamstack_*` variable namespace is intentional.

## [0.1.0] - 2026-09-28

Initial public alpha release.

### Added

- Composable Ansible role families for digital modes, packet/APRS/BBS, voice/hotspot
  appliances, visual tools, shared services, desktops, infrastructure, and network
  integrations.
- Local inventory model with Ansible Vault support and shared hardware-resource
  definitions.
- Interactive configurator plus non-interactive inventory/bootstrap helpers.
- Deployment profiles for a HamCube/service node, conference control station, and
  contributor workstation.
- Packet stack support including Graywolf, APRS, LinBPQ, Pat/Winlink, and an IP-access
  ENiGMA BBS deployment.
- Digital/operator support including FLDIGI, FLRIG, WSJT-X, JS8Call, FT8Web, SSTV,
  CHIRP, NetLogger, UniPager, and multimon-ng.
- Appliance configuration for preinstalled AllStarLink ASL3 and WPSD systems.
- Shared/event services including Gatus, DCDash, Blur Deck, CONHAM display mirroring,
  Meshtastic Web, Cloudlog, Wavelog, GPS-backed time, OpenHamClock, and OpenWebRX.
- Network/infrastructure roles for 44Net Connect, Technitium DNS, basic iPXE content,
  read-only AREDN integration, OpenWrt/GL.iNet, and RouterOS.
- Offline repository QA, variable-reference generation, contributor guidance, security
  guidance, architecture documentation, and agent/maintainer instructions.

### Release expectations

- v0.1.0 is an alpha-quality public release, not a certification of every supported
  radio, interface, router, or appliance combination.
- Representative HRV hardware and deployment paths have been exercised; site-specific
  radio/audio calibration, device mapping, and application preferences may still need
  operator adjustment.
- Transmit-capable paths use conservative defaults and require the deploying operator
  to validate RF, PTT, audio, licensing, and local operating requirements.
