# HamStack deployment profiles

HamStack roles describe **capabilities**. Profiles describe useful combinations
of those capabilities for recognizable machines.

Profiles are thin playbooks, not mega-roles. Operators can copy, edit, override,
or ignore them without changing the underlying role architecture.

## Development workstation

`playbooks/profiles/dev-workstation.yml` prepares an apt/Debian-family machine
for HamStack development. It expects an already-provided HamStack source tree
and intentionally has no IDE or Git-hosting opinion.

## Control station

`playbooks/profiles/control-station.yml` prepares the lead volunteer/operator
workstation that runs HamStack playbooks against conference infrastructure. It
contains controller dependencies, not shared service workloads.

## HamCube / central service node

`playbooks/profiles/hamcube.yml` expresses the current central service/display
pattern. Its baseline enables Gatus, CONHAM display, Blur Deck media service,
and a Chromium kiosk. Technitium DNS and OpenHamClock are opt-in profile
features. Every profile toggle is inventory-overridable; the profile supplies
default composition rather than a fixed appliance definition.

When the kiosk toggle is enabled (the default), set `hamstack_operator_user` to the
existing desktop login that should run Chromium. The profile does not create a desktop
session or configure display-manager autologin.

The profile is not tied to a literal HamCube. A Pi 5 with NVMe, a mini-PC, or a
suitable laptop may all fill the same architectural role.

## Running a profile locally

The profile host expression can be overridden. This is useful during initial
workstation bootstrap:

```bash
ansible-playbook -i 'localhost,' -c local \
  playbooks/profiles/control-station.yml \
  -e hamstack_profile_hosts=localhost \
  -e hamstack_operator_user="$USER" \
  -e hamstack_controller_user="$USER" \
  -e hamstack_controller_repo_path="$PWD" \
  --ask-become-pass
```

For normal inventory use, create groups such as `hamcube`, `control_station`, or
`dev_workstation` and run the profile without the host override. If the source tree
is not at the role default `~/hamstack`, set `hamstack_controller_repo_path` or
`hamstack_dev_repo_path` in inventory.

## HamCube profile toggles

The HamCube defaults can be changed in inventory without editing the profile:

```yaml
hamstack_profile_hamcube_gatus: true
hamstack_profile_hamcube_conham: true
hamstack_profile_hamcube_blur_deck: true
hamstack_profile_hamcube_kiosk: true
hamstack_profile_hamcube_technitium: false
hamstack_profile_hamcube_openhamclock: false

# Optional: point the kiosk at something other than local Gatus.
hamstack_profile_hamcube_kiosk_url: https://conham.hamstack.home.arpa/
```

## SSTV booth

`playbooks/profiles/sstv-booth.yml` composes `digital/slowrxd`,
`digital/sstv_booth`, and `desktop/kiosk` for a single-Pi event booth that shows
received SSTV images and sends pedal-triggered selfies. The profile points the
slowrxd hook and the kiosk at the booth's local port
(`hamstack_sstv_booth_http_port`). Set `hamstack_profile_sstv_booth_kiosk: false`
to skip the kiosk, or `hamstack_profile_sstv_booth_hook_url` to send hook events
elsewhere. Transmission stays disabled until `hamstack_sstv_booth_tx_enabled` is
set. See `inventory/example/host_vars/sstv-booth-node.yml`.

## APRS kiosk

`playbooks/profiles/aprs-kiosk.yml` composes `packet/graywolf`, `packet/aprs`,
optional `digital/cw_practice`, and `desktop/kiosk` for a receive-only APRS
display station. Graywolf decodes AFSK1200 from an AIOC. The example host_vars
keep APRS simulation mode on with beaconing, digipeating, and IS-to-RF gating
off, and leave the RF-to-IS iGate as an opt-in. The kiosk can rotate between the
Graywolf UI and other pages (`hamstack_kiosk_urls`,
`hamstack_kiosk_rotate_interval_s`; X11 required).

Profile toggles:

```yaml
hamstack_profile_aprs_kiosk_aprs: true    # packet/aprs policy on top of Graywolf
hamstack_profile_aprs_kiosk_cw: false     # CW practice page and GPIO Morse key
hamstack_profile_aprs_kiosk_kiosk: true   # Chromium kiosk
```

See `inventory/example/host_vars/aprs-kiosk-node.yml`.
