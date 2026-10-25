# HamStack features

HamStack is a community-oriented Ansible framework for building reproducible
amateur-radio, event, lab, and station infrastructure.

It began with Ham Radio Village conference systems, but the roles are intended
to be useful to clubs, individual operators, event teams, makerspaces, and
anyone else who wants to build the same station twice.

## Status legend

HamStack v0.1.x uses the following maturity language:

- **Implemented** — the role is deployable, passes repository QA, and has a documented
  automation boundary.
- **Reference exercised** — the capability has additionally been exercised on an HRV
  reference deployment; site-specific tuning may still be required.
- **Partial by design** — the useful baseline is implemented while advanced, unsafe-to-
  infer, or hardware-specific behavior remains with the upstream project/operator.
- **Planned** — documented future work, not a deployable capability.

No status should be read as certification for every supported radio, router, appliance,
or conference network. See [`docs/role-status.md`](docs/role-status.md) and
[`docs/qa.md`](docs/qa.md).

## Amateur-radio applications

| Capability | HamStack role(s) | Current state |
| --- | --- | --- |
| FLDIGI digital modes | `digital/fldigi` | Implemented |
| FLRIG rig control | `digital/flrig` | Implemented; reference workstation exercised |
| WSJT-X | `digital/wsjtx` | Implemented; reference workstation exercised |
| JS8Call | `digital/js8call` | Implemented |
| Browser-based FT8 | `digital/ft8web` | Implemented; local mirror |
| POCSAG/general decoding | `digital/multimon-ng` | Implemented |
| POCSAG paging | `digital/unipager` | Implemented; RF configuration remains operator-owned |
| Radio programming | `desktop/chirp` | Implemented |
| Net operations | `desktop/netlogger` | Implemented; operator supplies supported installer |

## Packet, APRS, and messaging

| Capability | HamStack role(s) | Current state |
| --- | --- | --- |
| Software TNC/modem service | `packet/graywolf` | Implemented; reference deployment exercised |
| APRS conference profile | `packet/aprs` | Implemented; advanced beacon/digi CRUD partial by design |
| BPQ node/BBS | `packet/linbpq` | Implemented; operator supplies LinBPQ binary |
| ENiGMA BBS | `packet/enigma-bbs` | IP services implemented; RF KISS/AX.25 shim planned |
| Winlink | `packet/winlink` | Implemented Pat deployment with operator-selected transports |

## Voice and hotspot appliances

| Capability | HamStack role(s) | Current state |
| --- | --- | --- |
| AllStarLink / ASL3 | `voice/allstar` | Reference exercised on a preinstalled upstream system; calibration remains site-specific |
| WPSD hotspot | `voice/wpsd` | Reference exercised on a pre-imaged upstream appliance; provider/account policy remains upstream-managed |

HamStack does not generally replace upstream appliance images. Install the
supported appliance, make it reachable, and let HamStack configure the portion
it owns.

## Visual, SDR, and station display

| Capability | HamStack role(s) | Current state |
| --- | --- | --- |
| SSTV receive appliance | `digital/sstv-rx` | Reference exercised; GQRX + HRV QSSTV receive path implemented |
| SSTV workstation | `digital/sstv-workstation` | Implemented; detailed per-user audio/PTT preferences remain operator-configured |
| SSTV Selfie Station | `digital/selfie_station` | Implemented; reference workflow exercised; TX disabled by default |
| SSTV booth (receive display + pedal selfie TX) | `digital/slowrxd`, `digital/sstv_booth` | Implemented; repository and dev-mode tested, not yet hardware validated; TX disabled by default |
| CW practice page and GPIO Morse key | `digital/cw_practice` | Implemented; not yet hardware validated |
| GridTracker2 | `visual/gridtracker` | Implemented; reference workstation exercised |
| OpenWebRX | `visual/openwebrx` | Implemented container deployment |
| OpenHamClock | `visual/openhamclock` | Implemented container deployment |
| Generic browser kiosk | `desktop/kiosk` | Implemented; optional multi-URL tab rotation (X11) |
| Conference Blur Deck to Roku/DLNA | `services/blur-deck` | Implemented |
| Local CONHAM conference RF information | `services/conham-display` | Implemented last-known-good mirror |

## Shared services

| Capability | HamStack role(s) | Current state |
| --- | --- | --- |
| Deployment/status dashboard | `services/gatus` | Implemented |
| Contest scoreboard | `services/dcdash` | Implemented |
| Meshtastic Web | `services/meshtastic-dashboard` | Implemented |
| Cloudlog | `services/cloudlog` | Local server implemented; application setup remains upstream-managed |
| Wavelog | `services/wavelog` | Local server implemented; application setup remains upstream-managed |
| GNSS/PPS-backed NTP | `services/gps-time` | Implemented |

## Network and infrastructure

| Capability | HamStack role(s) | Current state |
| --- | --- | --- |
| 44Net Connect / WireGuard | `network/44connect` | Implemented; split-route by default |
| OpenWrt / GL.iNet | `network/openwrt` | Conservative backend; validate on target hardware before cutover |
| MikroTik RouterOS | `network/routeros` | Conservative backend; validate on target hardware before cutover |
| AREDN integration | `network/aredn` | Read-only monitoring/integration |
| Local DNS | `infrastructure/technitium-dns` | Implemented Technitium DNS deployment |
| Basic netboot/iPXE content | `infrastructure/netboot` | HTTP/iPXE service implemented; DHCP/TFTP intentionally out of scope |

Network appliances are managed through their own inventory and playbook rather
than being treated like ordinary Debian nodes.

## Operator and contributor workstations

| Capability | HamStack role(s) | Current state |
| --- | --- | --- |
| Conference Ansible controller | `desktop/hamstack-controller` | Implemented |
| Debian-family contributor environment | `desktop/hamstack-dev` | Implemented |
| Kiosk/presentation client | `desktop/kiosk` | Implemented |

The workstation roles intentionally do not impose an IDE or Git workflow. They
prepare an already-provided HamStack source tree for use.

## Deployment profiles

HamStack roles are intentionally small and composable. Profiles provide useful
starting combinations without turning a machine name into a giant role.

Current profiles:

- **HamCube** — central service/display node baseline;
- **control station** — lead-volunteer Ansible control workstation;
- **development workstation** — Debian-family contributor environment.

See [`docs/profiles.md`](docs/profiles.md).

## Hardware/resource model

HamStack inventory can describe reusable named resources such as:

- AIOC and DigiRig interfaces;
- serial/audio/PTT endpoints;
- cameras and HID triggers;
- GPS/PPS receivers;
- RTL-SDR devices;
- radios and CAT/PTT metadata.

Roles reference the resource by name rather than assuming that a particular USB
device, Pi number, or hostname always performs a particular job.

## Conference and offline resilience

Where useful, HamStack favors local capability over dependence on conference
Internet access. Current examples include:

- local CONHAM mirroring with last-known-good behavior;
- local DCDash/Gatus/logging services;
- local DNS;
- local Blur Deck media distribution;
- local FT8Web mirror;
- local packet/BBS services.

This is a design preference rather than a guarantee that every upstream
application works completely offline.

## Configuration and QA

HamStack includes:

- example inventory and host variables;
- Ansible Vault integration;
- an interactive terminal configurator;
- generated exhaustive variable documentation;
- target-node and workstation bootstrap scripts;
- static repository QA;
- documented live/idempotency validation procedures.

Start with [`docs/getting-started.md`](docs/getting-started.md).
