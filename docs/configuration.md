# HamStack configuration reference

> **Schema version:** 0.1
> **Status:** initial public configuration contract; role implementations are still evolving.

HamStack separates **site identity**, **host resources**, **role configuration**, and **secrets**. The intent is that a neighborhood, club, event team, or individual operator can clone HamStack, create a private local inventory, describe the hardware actually attached to each node, and then enable/configure whatever HamStack roles that node should provide.

The variables documented here are the public HamStack configuration vocabulary for schema v0.1. A variable appearing here is intended to be stable enough for operators and role authors to use. Implementation-specific upstream settings should remain inside a role unless they need to become part of this public contract.

For an exhaustive generated list of every currently declared `hamstack_*` variable and its default, see [variables.md](variables.md). The generated index is checked by the repository QA script so new role defaults cannot silently drift out of the documented configuration surface.

## First-time setup

From the repository root:

```bash
bash ./scripts/init-local-inventory.sh
```

The manual equivalent is:

```bash
cp -R inventory/example inventory/local
```

Then:

1. Edit `inventory/local/hosts.yml` and replace the example node with your real host(s).
2. Rename `inventory/local/host_vars/example-node.yml` so the filename matches the inventory hostname it configures.
3. Edit `inventory/local/group_vars/all.yml` with site-wide values such as callsign, grid, and timezone.
4. Edit each host's `host_vars/<hostname>.yml` to describe attached hardware and host-specific role settings.
5. If a role needs credentials, create `inventory/local/group_vars/all/vault.yml` with Ansible Vault.
6. Test the inventory with `ansible all -m ping`.

`inventory/local/` is ignored by Git and is the normal place for real deployment data.

## Secrets

Do not put real credentials in `group_vars/all.yml`, role defaults, README files, or the tracked example inventory.

Create an encrypted local vault:

```bash
ansible-vault create inventory/local/group_vars/all/vault.yml
```

The file `inventory/example/group_vars/all/vault.yml.example` lists the secret variable names currently reserved by HamStack. Only define the secrets your deployment actually needs. The playbooks also load `inventory/local/group_vars/all/vault.yml` explicitly when it exists, keeping secret handling predictable across supported Ansible layouts.

## Configuration precedence

HamStack uses these conceptual layers:

```text
role defaults
    ↓
site variables in inventory/local/group_vars/all.yml
    ↓
host variables in inventory/local/host_vars/<host>.yml
    ↓
encrypted vault variables
```

Ansible's normal variable-precedence rules still apply. The important project convention is that shared site identity belongs in `group_vars`, attached physical resources and per-node role configuration belong in `host_vars`, and credentials belong in Vault.

## Site and host variables

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_site_name` | string | `HamStack` | site | Human-readable name for this HamStack deployment. |
| `hamstack_event_name` | string | `""` | site | Optional event or temporary deployment name shared by roles that display or log event context. |
| `hamstack_callsign` | string | `N0CALL` | site | Default amateur-radio callsign for the deployment. Roles may override it when a service uses another callsign. |
| `hamstack_grid_locator` | string | `""` | site | Default Maidenhead grid locator for the deployment. |
| `hamstack_latitude` | number/null | `null` | site | Default station latitude in decimal degrees. |
| `hamstack_longitude` | number/null | `null` | site | Default station longitude in decimal degrees. |
| `hamstack_country_code` | string | `US` | site | Two-letter country code used by roles that need regional defaults. |
| `hamstack_timezone` | string | `Etc/UTC` | site | IANA timezone name for managed hosts. |
| `hamstack_locale` | string | `en_US.UTF-8` | site | Default locale for managed hosts. |
| `hamstack_config_dir` | path | `/etc/hamstack` | site | Directory for HamStack-owned configuration and generated metadata. |
| `hamstack_data_dir` | path | `/var/lib/hamstack` | site | Directory for persistent HamStack-owned data. |
| `hamstack_cache_dir` | path | `/var/cache/hamstack` | site | Directory for disposable HamStack caches. |
| `hamstack_log_dir` | path | `/var/log/hamstack` | site | Directory for HamStack-owned logs when a role does not use an upstream-native log location. |
| `hamstack_operator_user` | string | `""` | host | Linux login/session account used by desktop-oriented HamStack roles such as FLDIGI, FLRIG, WSJT-X, and QSSTV. Required when a role manages per-user autostart or configuration. |
| `hamstack_manage_hostname` | boolean | `false` | host | Whether the common role should manage the operating-system hostname. |
| `hamstack_hostname` | string | `{{ inventory_hostname }}` | host | Desired hostname when hostname management is enabled. |
| `hamstack_manage_timezone` | boolean | `true` | host | Whether the common role should configure the system timezone. |
| `hamstack_manage_locale` | boolean | `false` | host | Whether the common role should configure the system locale. Reserved for the common-role implementation. |
| `hamstack_devices` | dictionary | `{}` | host | Registry of reusable hardware devices attached to this host. Device resources may be consumed by multiple roles. |
| `hamstack_radios` | dictionary | `{}` | host | Registry of radios available to this host. Radios may refer to entries in hamstack_devices and be consumed by multiple roles. |

## Shared hardware resources

### `hamstack_devices`

`hamstack_devices` is a host-scoped dictionary of **named physical or logical devices**. It exists specifically so multiple roles can refer to the same AIOC, DigiRig, SDR, camera, GPS receiver, USB audio interface, HID trigger, or other shared resource without independently rediscovering or redefining it.

A device entry uses this schema:

```yaml
hamstack_devices:
  aioc_main:
    type: aioc
    description: Primary AIOC
    match:
      usb_vendor_id: ""
      usb_product_id: ""
      usb_serial: ""
    endpoints:
      serial: ""
      audio_capture: ""
      audio_playback: ""
      video: ""
      hid: ""
    options: {}
```

Common keys:

| Key | Purpose |
| --- | --- |
| `type` | Logical device type, for example `aioc`, `digirig`, `usb_audio`, `rtl_sdr`, `gps`, `camera`, `hid`, `serial`, or another role-supported type. |
| `description` | Human-readable description for operators. |
| `match` | Stable discovery hints such as USB vendor/product IDs or serial number. |
| `endpoints` | Resolved/explicit OS endpoints such as serial, audio capture/playback, video, or HID paths/identifiers. |
| `options` | Device-type-specific settings that do not yet justify first-class schema keys. |

Roles should reference a device by its dictionary key, for example `aioc_main`, rather than duplicate the USB/audio/serial details.

### `hamstack_radios`

`hamstack_radios` is a host-scoped registry of radios available to roles on the node.

```yaml
hamstack_radios:
  uhf_main:
    model: Generic UHF radio
    description: UHF packet/SSTV radio
    interface: aioc_main
    cat:
      device: ""
      baud: null
      data_bits: null
      stop_bits: null
      flow_control: ""
    ptt:
      method: ""
      device: ""
    options: {}
```

Common keys:

| Key | Purpose |
| --- | --- |
| `model` | Human-readable or upstream-recognized radio model. |
| `description` | Operator-facing description. |
| `interface` | Default named entry in `hamstack_devices` used by the radio. |
| `cat` | Shared CAT/rig-control settings where applicable. |
| `ptt` | Shared PTT method/device settings where applicable. |
| `options` | Radio-specific settings not yet promoted to the public schema. |

A radio definition intentionally does **not** own operating frequency, packet modem mode, SSTV mode, or another application's behavior. Those belong to the consuming role.

## Role variables

<a id="role-common"></a>
### `common`

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_common_manage_packages` | boolean | `true` | role | Install and maintain the baseline package set. |
| `hamstack_common_packages` | list[string] | `["curl", "git", "htop", "jq", "rsync", "tmux", "unzip", "vim", "wget"]` | role | Baseline packages expected on HamStack-managed nodes. |
| `hamstack_common_extra_packages` | list[string] | `[]` | role | Additional site- or host-specific packages to install with the baseline. |
| `hamstack_common_apt_cache_valid_time` | integer | `3600` | role | Seconds an existing apt cache is considered fresh on Debian-family systems. |
| `hamstack_common_manage_directories` | boolean | `true` | role | Create the HamStack config/data/cache/log directories. |
| `hamstack_common_manage_udev_rules` | boolean | `false` | role | Render `/etc/udev/rules.d/90-hamstack-devices.rules` from `hamstack_devices` entries that define a `udev` mapping. |

When udev management is enabled, a device such as the AIOC can request a stable
symlink. The rule matches `match.usb_vendor_id`/`usb_product_id` (and
`usb_serial` when set):

```yaml
hamstack_devices:
  aioc_main:
    type: aioc
    match:
      usb_vendor_id: "1209"
      usb_product_id: "7388"
    udev:
      subsystem: hidraw      # default
      symlink: aioc-ptt      # creates /dev/aioc-ptt
      group: audio           # default
      mode: "0660"           # default
```

HamStack owns that rules file; put operator rules in a separate file.


### Digital

<a id="role-fldigi"></a>
#### `fldigi`

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_fldigi_enabled` | boolean | `false` | role | Enable management of FLDIGI on this host. |
| `hamstack_fldigi_install` | boolean | `true` | role | Allow the role to install FLDIGI using its supported installation method. |
| `hamstack_fldigi_callsign` | string | `{{ hamstack_callsign \| default('N0CALL') }}` | role | Callsign presented to FLDIGI. |
| `hamstack_fldigi_grid_locator` | string | `{{ hamstack_grid_locator \| default('') }}` | role | Grid locator presented to FLDIGI. |
| `hamstack_fldigi_radio` | resource name | `""` | role | Name of a radio in hamstack_radios. |
| `hamstack_fldigi_interface` | resource name | `""` | role | Optional device in hamstack_devices used directly for audio/PTT when not fully described by the radio resource. |
| `hamstack_fldigi_rig_control` | enum | `none` | role | Rig-control integration: none, flrig, or a supported direct-control backend. |
| `hamstack_fldigi_xmlrpc_bind` | string | `127.0.0.1` | role | Address for FLDIGI XML-RPC when enabled by the implementation. |
| `hamstack_fldigi_xmlrpc_port` | integer/null | `null` | role | FLDIGI XML-RPC port. null means use the supported upstream/default value. |
| `hamstack_fldigi_autostart` | boolean | `false` | role | Start FLDIGI automatically in the supported session/service model. |
| `hamstack_fldigi_config_dir` | path/string | `""` | role | Override the upstream/default FLDIGI configuration directory. |
| `hamstack_fldigi_extra_settings` | dictionary | `{}` | role | Escape hatch for supported FLDIGI settings not yet promoted to first-class variables. |

<a id="role-flrig"></a>
#### `flrig`

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_flrig_enabled` | boolean | `false` | role | Enable management of FLRIG on this host. |
| `hamstack_flrig_install` | boolean | `true` | role | Allow the role to install FLRIG using its supported installation method. |
| `hamstack_flrig_radio` | resource name | `""` | role | Name of a radio in hamstack_radios. |
| `hamstack_flrig_interface` | resource name | `""` | role | Optional device in hamstack_devices used for CAT/PTT when not fully described by the radio resource. |
| `hamstack_flrig_rig_model` | string | `""` | role | Optional upstream rig-model override when the model cannot be derived from hamstack_radios. |
| `hamstack_flrig_serial_baud` | integer/null | `null` | role | Optional serial-speed override for CAT control. |
| `hamstack_flrig_xmlrpc_bind` | string | `127.0.0.1` | role | Address for the FLRIG XML-RPC service. |
| `hamstack_flrig_xmlrpc_port` | integer/null | `null` | role | FLRIG XML-RPC port. null means use the supported upstream/default value. |
| `hamstack_flrig_autostart` | boolean | `false` | role | Start FLRIG automatically in the supported session/service model. |
| `hamstack_flrig_config_dir` | path/string | `""` | role | Override the upstream/default FLRIG configuration directory. |
| `hamstack_flrig_extra_settings` | dictionary | `{}` | role | Escape hatch for supported FLRIG settings not yet promoted to first-class variables. |

<a id="role-wsjtx"></a>
#### `wsjtx`

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_wsjtx_enabled` | boolean | `false` | role | Enable management of WSJT-X on this host. |
| `hamstack_wsjtx_install` | boolean | `true` | role | Allow the role to install WSJT-X using its supported installation method. |
| `hamstack_wsjtx_callsign` | string | `{{ hamstack_callsign \| default('N0CALL') }}` | role | Callsign presented to WSJT-X. |
| `hamstack_wsjtx_grid_locator` | string | `{{ hamstack_grid_locator \| default('') }}` | role | Grid locator presented to WSJT-X. |
| `hamstack_wsjtx_radio` | resource name | `""` | role | Name of a radio in hamstack_radios. |
| `hamstack_wsjtx_interface` | resource name | `""` | role | Optional device in hamstack_devices used directly for audio/CAT/PTT. |
| `hamstack_wsjtx_rig_control` | enum | `flrig` | role | Rig-control backend: flrig, direct, hamlib, or none as supported. |
| `hamstack_wsjtx_udp_server_address` | string | `127.0.0.1` | role | UDP destination used for WSJT-X status/decode messages. |
| `hamstack_wsjtx_udp_server_port` | integer | `2237` | role | UDP port used for WSJT-X status/decode messages. |
| `hamstack_wsjtx_autostart` | boolean | `false` | role | Start WSJT-X automatically in the supported session/service model. |
| `hamstack_wsjtx_config_dir` | path/string | `""` | role | Override the upstream/default WSJT-X configuration directory. |
| `hamstack_wsjtx_extra_settings` | dictionary | `{}` | role | Escape hatch for supported WSJT-X settings not yet promoted to first-class variables. |

### Network

<a id="role-44connect"></a>
#### `44connect`

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_44connect_enabled` | boolean | `false` | role | Enable 44Net Connect on this host. |
| `hamstack_44connect_mechanism` | enum | `wireguard` | role | Connection backend; the supported backend is WireGuard. |
| `hamstack_44connect_interface_name` | string | `ham44` | role | WireGuard interface/config name. |
| `hamstack_44connect_address` | CIDR/string | `""` | role | Address assigned by 44Net Connect. |
| `hamstack_44connect_mtu` | integer/null | `null` | role | Optional MTU from the downloaded tunnel. |
| `hamstack_44connect_split_tunnel` | boolean | `true` | role | Route only 44Net traffic through the tunnel. |
| `hamstack_44connect_allowed_ips` | list[string] | `44.0.0.0/9`, `44.128.0.0/10` | role | Default split-tunnel WireGuard AllowedIPs. |
| `hamstack_44connect_full_tunnel_allowed_ips` | list[string] | `0.0.0.0/0` | role | AllowedIPs used when split tunnel is explicitly disabled. |
| `hamstack_44connect_routes` | list[string] | `[]` | role | Additional AllowedIPs/routes appended by the deployment. |
| `hamstack_44connect_dns_servers` | list[string] | `[]` | role | Optional DNS entries from the tunnel config. |
| `hamstack_44connect_peer_public_key` | string | `""` | role | 44Net Connect peer public key. |
| `hamstack_44connect_peer_endpoint` | string | `""` | role | Peer endpoint in `host:port` form. |
| `hamstack_44connect_persistent_keepalive` | integer | `25` | role | WireGuard PersistentKeepalive. |
| `hamstack_44connect_autostart` | boolean | `true` | role | Enable/start `wg-quick@<interface>`. |
| `hamstack_44connect_restart_on_change` | boolean | `true` | role | Restart an active tunnel when its config changes. |
| `hamstack_44connect_private_key` | secret-derived string | Vault | role | Runtime private key, normally sourced from Vault. |
| `hamstack_44connect_preshared_key` | secret-derived string | Vault/empty | role | Optional WireGuard preshared key. |

The role never requests a tunnel from the 44Net portal; it consumes the values from an already-provisioned 44Net Connect tunnel.

<a id="role-aredn"></a>
#### `aredn`

`network/aredn` is a read-only integration role for already-running AREDN
nodes. It polls the documented `/a/sysinfo` API from a normal HamStack Linux
node, caches last-known-good JSON, and can contribute reachability checks to
Gatus. HamStack does not flash or configure AREDN firmware.

Core configuration is the `hamstack_aredn_nodes` list plus polling/optional API
flags. See `docs/variables.md` and the role README for the exhaustive current
variable surface.

### Packet

<a id="role-aprs"></a>
#### `aprs`

The first APRS implementation is a profile layered on Graywolf. Graywolf owns audio/PTT/radio channels; this role configures APRS behavior through Graywolf's REST API.

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_aprs_enabled` | boolean | `false` | role | Enable APRS profile management. |
| `hamstack_aprs_backend` | enum | `graywolf` | role | APRS backend; the supported backend is Graywolf. |
| `hamstack_aprs_callsign` | string | site callsign | role | Base station callsign. |
| `hamstack_aprs_ssid` | integer | `0` | role | APRS SSID 0-15. |
| `hamstack_aprs_graywolf_api_url` | URL | `http://127.0.0.1:8080/api` | role | Graywolf management API base. |
| `hamstack_aprs_graywolf_channel_id` | integer/null | `null` | role | Existing Graywolf RF channel ID. |
| `hamstack_aprs_simulation_mode` | boolean | `true` | role | Keep Graywolf TX muted while validating a demo configuration. |
| `hamstack_aprs_path` | list[string] | `[WIDE1-1]` | role | Originated RF path reserved for beacon/rule work. |
| `hamstack_aprs_beacon_enabled` | boolean | `false` | role | Request managed position beaconing; guarded until identity-safe live CRUD behavior is validated. |
| `hamstack_aprs_beacon_interval_seconds` | integer | `1800` | role | Desired beacon interval. |
| `hamstack_aprs_beacon_comment` | string | `""` | role | Desired beacon comment. |
| `hamstack_aprs_beacon_send_path` | enum | `rf` | role | `rf`, `both`, or `is_only`. |
| `hamstack_aprs_beacon_use_gps` | boolean | `false` | role | Use live GPS for the future managed beacon. |
| `hamstack_aprs_igate_enabled` | boolean | `false` | role | Enable Graywolf APRS-IS iGate. |
| `hamstack_aprs_igate_server` | string | `rotate.aprs2.net` | role | APRS-IS server. |
| `hamstack_aprs_igate_port` | integer | `14580` | role | APRS-IS port. |
| `hamstack_aprs_igate_server_filter` | string | `""` | role | APRS-IS server-side filter. |
| `hamstack_aprs_igate_rf_to_is` | boolean | `true` | role | Gate received RF packets to APRS-IS when iGate is enabled. |
| `hamstack_aprs_igate_is_to_rf` | boolean | `false` | role | Gate APRS-IS traffic back to RF; conservative default is off. |
| `hamstack_aprs_igate_tx_channel` | integer/null | `null` | role | Graywolf TX channel used for IS→RF. |
| `hamstack_aprs_digipeater_enabled` | boolean | `false` | role | Enable Graywolf digipeater behavior. |
| `hamstack_aprs_digipeater_callsign` | string | inherited station call | role | Optional separate digi callsign. |
| `hamstack_aprs_digipeater_dedupe_window_seconds` | integer | `30` | role | Graywolf duplicate suppression window. |
| `hamstack_aprs_digipeater_rules` | list[dictionary] | `[]` | role | Reserved managed rule set; guarded until identity-safe live CRUD behavior is validated. |

<a id="role-enigma-bbs"></a>
#### `enigma-bbs`

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_enigma_bbs_enabled` | boolean | `false` | role | Enable ENiGMA BBS. |
| `hamstack_enigma_bbs_image` | string | `enigmabbs/enigma-bbs:latest` | role | Official ENiGMA container image. |
| `hamstack_enigma_bbs_system_name` | string | `<site> BBS` | role | Board name. |
| `hamstack_enigma_bbs_description` | string | HamStack conference description | role | Board description. |
| `hamstack_enigma_bbs_packet_transport` | enum | `none` | role | Supported deployment is IP-only; a future value may represent Graywolf/KISS shim integration. |
| `hamstack_enigma_bbs_telnet_port` | integer | `8888` | role | Published Telnet port. |
| `hamstack_enigma_bbs_ssh_port` | integer | `8889` | role | Published SSH port. |
| `hamstack_enigma_bbs_websocket_internal_port` | integer | `8890` | role | Container-private plaintext WS port. |
| `hamstack_enigma_bbs_https_port` | integer | `8445` | role | Published Caddy HTTPS/WSS port. |
| `hamstack_enigma_bbs_tls_host` | string | inventory hostname | role | Name/IP for Caddy internal certificate. |
| `hamstack_enigma_bbs_data_dir` | path | `<hamstack_data_dir>/enigma-bbs` | role | Persistent DB/log/filebase/mail/Caddy data. |

The Graywolf KISS→AX.25 session→ENiGMA shim is planned but not part of the current public capability.

<a id="role-graywolf"></a>
#### `graywolf`

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_graywolf_enabled` | boolean | `false` | role | Enable Graywolf management on this host. |
| `hamstack_graywolf_install` | boolean | `true` | role | Install the supported upstream Debian package. |
| `hamstack_graywolf_version` | string | `latest` | role | Release to install, or a pinned upstream version. |
| `hamstack_graywolf_package_url` | string | `""` | role | Optional direct `.deb` URL (HTTPS), bypassing release discovery. |
| `hamstack_graywolf_package_checksum` | string | `""` | role | Optional `sha256:<digest>` verified before the package is installed. |
| `hamstack_graywolf_autostart` | boolean | `true` | role | Enable/start the Graywolf systemd service. |
| `hamstack_graywolf_manage_api` | boolean | `false` | role | Converge Graywolf operational state through its REST API. |
| `hamstack_graywolf_api_url` | URL | `http://127.0.0.1:8080/api` | role | Graywolf management API base. |
| `hamstack_graywolf_username` | string | `hamstack` | role | Management account used by automation. |
| `hamstack_graywolf_password` | secret | Vault | role | Management password; prefer `vault_hamstack_graywolf_password`. |
| `hamstack_graywolf_manage_first_user` | boolean | `true` | role | Create the first Graywolf management user on an unconfigured node. |
| `hamstack_graywolf_manage_station` | boolean | `true` | role | Converge Graywolf's station callsign. |
| `hamstack_graywolf_callsign` | string | site callsign | role | Station-wide Graywolf identity. |
| `hamstack_graywolf_audio_devices` | list[dictionary] | `[]` | role | Named input/output audio devices managed through Graywolf's API. |
| `hamstack_graywolf_channels` | list[dictionary] | `[]` | role | Named radio/modem channels, optional PTT, and optional KISS endpoints. |
| `hamstack_graywolf_agw` | dictionary | loopback:8000, disabled | role | Global AGWPE listener configuration. |
| `hamstack_graywolf_extra_settings` | dictionary | `{}` | role | Reserved settings not yet promoted to first-class variables. |

Graywolf API management is intentionally independent of `packet/aprs`. A host may run Graywolf solely as a packet modem/TNC and expose KISS or AGWPE to LinBPQ, Pat/Winlink, or another client. `packet/aprs` is an optional higher-level policy role.

Example packet-only modem configuration:

```yaml
hamstack_graywolf_manage_api: true

hamstack_graywolf_audio_devices:
  - name: packet_rx
    direction: input
    source_type: soundcard
    device_path: plughw:CARD=Device,DEV=0
    sample_rate: 48000
    channels: 1
    format: s16le
    gain_db: 0
  - name: packet_tx
    direction: output
    source_type: soundcard
    device_path: plughw:CARD=Device,DEV=0

hamstack_graywolf_channels:
  - name: packet_2m
    mode: packet
    input_device: packet_rx
    output_device: packet_tx
    modem: afsk1200
    frequency_mhz: null   # inventory/operator metadata; Graywolf does not tune the radio
    ptt:
      method: cm108
      device_path: /dev/hidraw0
      gpio_pin: 3
    kiss:
      enabled: true
      type: tcp
      listen_address: 127.0.0.1
      port: 6700
      mode: modem
      allow_connected_mode: true

hamstack_graywolf_agw:
  enabled: true
  listen_address: 127.0.0.1
  port: 8000
  callsigns: K0HRV
```

Channel `mode` accepts `aprs`, `packet`, or `aprs+packet`. A channel with `kiss_tnc_only: true` omits audio/modem backing and can instead be bound to an external TNC through a Graywolf KISS interface. The role identifies audio devices and channels by name, so Graywolf's numeric database IDs remain internal implementation details.

<a id="role-linbpq"></a>
#### `linbpq`

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_linbpq_enabled` | boolean | `false` | role | Enable LinBPQ node/BBS. |
| `hamstack_linbpq_install` | boolean | `false` | role | Download an operator-selected upstream binary. |
| `hamstack_linbpq_binary_url` | URL | `""` | role | Compatible upstream binary URL (HTTPS) when install is enabled. |
| `hamstack_linbpq_binary_checksum` | string | `""` | role | Optional `sha256:<digest>` of the binary, verified on download. |
| `hamstack_linbpq_binary_path` | path | `/opt/linbpq/linbpq` | role | Executable path. |
| `hamstack_linbpq_node_callsign` | string | site callsign | role | Node callsign. |
| `hamstack_linbpq_node_alias` | string | `""` | role | NET/ROM node alias. |
| `hamstack_linbpq_bbs_enabled` | boolean | `true` | role | Enable LinMail/BBS application. |
| `hamstack_linbpq_bbs_callsign` | string | `""` | role | BBS application callsign. |
| `hamstack_linbpq_bbs_alias` | string | `BBS` | role | BBS alias. |
| `hamstack_linbpq_ports` | list[dictionary] | `[]` | role | KISS-over-TCP RF ports, normally pointed at Graywolf loopback endpoints. |
| `hamstack_linbpq_node_options` | dictionary | conservative conference-node defaults | role | BPQ node/routing/timer settings. |
| `hamstack_linbpq_telnet_enabled` | boolean | `false` | role | Enable Telnet/FBB service port. |
| `hamstack_linbpq_telnet_port` | integer | `8010` | role | User Telnet port. |
| `hamstack_linbpq_fbb_port` | integer | `8011` | role | FBB/transparent service port. |
| `hamstack_linbpq_web_port` | integer | `8080` | role | Web management port. |
| `hamstack_linbpq_telnet_users` | secret-derived list | Vault/empty | role | SYSOP/user records rendered into BPQ config. |

Every generated RF port uses `KISSOPTIONS=NOPARAMS` by default so Graywolf retains ownership of modem/PTT/timing. All callsigns, SSIDs, aliases, KISS endpoints, service ports, and per-port timing values are inventory variables.

<a id="role-winlink"></a>
#### `winlink`

`packet/winlink` currently means the Pat Winlink client. The role installs a
pinned upstream Pat Debian package, creates persistent mailbox/config storage,
renders Pat's native JSON configuration, and can run the local web UI as a
hardened systemd service.

Transport details remain explicit/operator-driven: Telnet is the minimal
default and native Pat settings are exposed for AX.25, AGWPE, serial TNC,
ARDOP, VARA, PACTOR, Hamlib, and GPSd integration. HamStack does not deploy
every modem/rig stack automatically.

Use `vault_hamstack_winlink_password` for the Winlink secure-login password.
The Pat package is downloaded into the root-owned HamStack package cache and
verified against `hamstack_winlink_package_checksums` (per-architecture
`sha256:<digest>` values for `hamstack_winlink_version`);
`hamstack_winlink_require_checksum` controls whether an unknown digest is an
error. See `docs/variables.md` and the role README for the exhaustive current
variable surface.

### Services

<a id="role-cloudlog"></a>
#### `cloudlog`

Deploys a **local Cloudlog server** using Apache, PHP, and MariaDB. HamStack
creates the database/user, checks out the selected upstream source, grants
write access only to Cloudlog runtime paths, and publishes an HTTPS virtual
host. Cloudlog's normal `/install` wizard and all station/user/logging workflow
remain upstream/operator configuration.

Core variables are `hamstack_cloudlog_source_repo`,
`hamstack_cloudlog_source_ref`, `hamstack_cloudlog_install_dir`, database name
and user, and the HTTPS bind/port. Store
`vault_hamstack_cloudlog_database_password` in Vault.

HamStack intentionally does not implement log synchronization or provider
middleware. See `docs/variables.md` for the exhaustive variable surface.

<a id="role-dcdash"></a>
#### `dcdash`

Deploys DCDash from an operator-selected git repository/ref into a Python
virtual environment with an application-scoped hardened systemd unit. DCDash
uses its native TLS service and public `/health` endpoint.

```yaml
hamstack_dcdash_enabled: true
hamstack_dcdash_source_repo: "https://example.invalid/dcdash.git"
hamstack_dcdash_source_ref: main
hamstack_dcdash_port: 8450
```

Store `vault_hamstack_dcdash_admin_password` in Vault. The role requires the
DCDash 2.9-supported Python 3.11 or 3.12 runtime. It deliberately does not copy
the standalone deploy script's host-wide firewall, SSH, fail2ban, Avahi, or
hostname policy.

<a id="role-gatus"></a>
#### `gatus`

Deploys Gatus in a container behind a Caddy internal-CA HTTPS sidecar. HamStack
can derive basic node/service checks from inventory and can append native Gatus
endpoint definitions through `hamstack_gatus_endpoints`. This is a lightweight
local status surface, not a bespoke HamStack monitoring product.

<a id="role-blur-deck"></a>
#### `blur-deck`

Installs ReadyMedia/MiniDLNA and publishes a managed video directory to Roku
Media Player and other DLNA clients. HamStack may copy an operator-supplied
media file into the directory, but rendering/generating the Blur Deck remains
outside this role.

<a id="role-conham-display"></a>
#### `conham-display`

Maintains a staged, last-known-good local mirror of the rendered `conham.radio`
site and serves it over local HTTPS. Failed refreshes leave the previous mirror
active, making the conference frequency information useful when WAN access is
poor. Markdown-native upstream builds and Roku-specific rendering are later
refinements; local HTML is the current supported representation.

<a id="role-meshtastic-dashboard"></a>
#### `meshtastic-dashboard`

Deploys the official Meshtastic Web client container behind the standard
HamStack Caddy HTTPS sidecar. Device selection/connection remains the upstream
Meshtastic Web workflow.

<a id="role-gps-time"></a>
#### `gps-time`

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_gps_time_enabled` | boolean | `false` | role | Enable GNSS-backed time service. |
| `hamstack_gps_time_device` | resource name | `""` | role | GPS entry in `hamstack_devices` with `endpoints.serial`. |
| `hamstack_gps_time_pps_enabled` | boolean | `false` | role | Use the receiver's PPS timing source. |
| `hamstack_gps_time_pps_device` | path | `""` | role | PPS device override; otherwise use `endpoints.pps`. |
| `hamstack_gps_time_refclock_mode` | enum | `auto` | role | `auto`, `sock`, or `shm`. Auto prefers gpsd SOCK for PPS and SHM for non-PPS compatibility. |
| `hamstack_gps_time_refid` | string | `GPS` | role | Chrony refclock identifier. |
| `hamstack_gps_time_nmea_offset_seconds` | number | `0.5` | role | NMEA timing offset for non-PPS timing. |
| `hamstack_gps_time_nmea_delay_seconds` | number | `0.1` | role | NMEA serial delay estimate. |
| `hamstack_gps_time_allow_networks` | list[CIDR] | `[]` | role | LANs allowed to query chronyd. Empty means localhost only. |

A GNSS/PPS receiver is the stratum-0 reference; the synchronized HamStack host serves clients as stratum 1.

<a id="role-wavelog"></a>
#### `wavelog`

Deploys a **local Wavelog service** using the upstream container model with a
MariaDB container, persistent application/database directories, and a Caddy
HTTPS sidecar. Finish Wavelog's normal application setup through its `/install`
workflow.

Store `vault_hamstack_wavelog_database_password` in Vault. HamStack does not
implement QSO federation, synchronization, or logging middleware; external
Cloudlog/Wavelog use and later import/export remain application/operator
workflows. See `docs/variables.md` for the complete variables.

<a id="role-gridtracker"></a>
#### `gridtracker`

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_gridtracker_enabled` | boolean | `false` | role | Enable GridTracker2. |
| `hamstack_gridtracker_install` | boolean | `true` | role | Install a Debian package. |
| `hamstack_gridtracker_version` | string | `2.260925.2` | role | Tested default or another pinned upstream version. |
| `hamstack_gridtracker_package_url` | URL | `""` | role | Explicit package override (HTTPS). |
| `hamstack_gridtracker_package_checksum` | string | `""` | role | Optional `sha256:<digest>` verified before the package is installed. |
| `hamstack_gridtracker_wsjtx_host` | string | `127.0.0.1` | role | Reserved WSJT-X input host setting. |
| `hamstack_gridtracker_wsjtx_port` | integer | `2237` | role | Reserved WSJT-X UDP port. |
| `hamstack_gridtracker_autostart` | boolean | `false` | role | Add XDG autostart for the operator user. |

Supported packages are available for amd64 and arm64 Debian-family systems.

<a id="role-openhamclock"></a>
#### `openhamclock`

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_openhamclock_enabled` | boolean | `false` | role | Enable OpenHamClock LAN service. |
| `hamstack_openhamclock_image` | string | `ghcr.io/accius/openhamclock:latest` | role | Upstream application container. |
| `hamstack_openhamclock_https_port` | integer | `8449` | role | Only host-published application port. |
| `hamstack_openhamclock_tls_host` | string | inventory hostname | role | Name/IP on Caddy internal certificate. |
| `hamstack_openhamclock_caddy_image` | string | `caddy:2-alpine` | role | TLS sidecar. |
| `hamstack_openhamclock_environment` | dictionary | `{}` | role | Supported upstream container environment overrides. |

The application HTTP port 3000 remains Docker-private; Caddy publishes HTTPS only.

<a id="role-openwebrx"></a>
#### `openwebrx`

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_openwebrx_enabled` | boolean | `false` | role | Enable OpenWebRX LAN service. |
| `hamstack_openwebrx_image` | string | `jketterl/openwebrx:stable` | role | OpenWebRX container image. |
| `hamstack_openwebrx_device_mappings` | list[string] | `[]` | role | Explicit Docker SDR device mappings. |
| `hamstack_openwebrx_https_port` | integer | `8444` | role | Only host-published application port. |
| `hamstack_openwebrx_tls_host` | string | inventory hostname | role | Name/IP on Caddy internal certificate. |
| `hamstack_openwebrx_data_dir` | path | `<hamstack_data_dir>/openwebrx` | role | Persistent settings/Caddy data. |

The OpenWebRX HTTP listener on 8073 remains Docker-private. Receiver profiles and admin-user provisioning are intentionally not automated yet.

<a id="role-selfie-station"></a>
#### `selfie_station`

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_selfie_station_enabled` | boolean | `false` | role | Enable the SSTV Selfie Station workflow. |
| `hamstack_selfie_station_user` | string | `hamstack-selfie` | role | Dedicated unprivileged Linux account that runs the headless Selfie Station service. Do not reuse the Ansible automation account. |
| `hamstack_selfie_station_group` | string | `hamstack-selfie` | role | Primary group of the service account. |
| `hamstack_selfie_station_manage_user` | boolean | `true` | role | Create the service account/group as a nologin system user. |
| `hamstack_selfie_station_user_groups` | list[string] | `audio`, `dialout`, `video`, `input` | role | Supplementary groups granting camera, audio, AIOC serial, and trigger-device access. |
| `hamstack_selfie_station_install_dir` | path | `/opt/hamstack/selfie_station` | role | Application deployment directory. |
| `hamstack_selfie_station_venv_dir` | path | `/opt/hamstack/selfie_station/venv` | role | Python virtual environment used by the service. |
| `hamstack_selfie_station_data_dir` | path | `{{ (hamstack_data_dir \| default('/var/lib/hamstack')) ~ '/selfie_station' }}` | role | Root for photos, generated SSTV images, and WAV files. |
| `hamstack_selfie_station_callsign` | string | `{{ hamstack_callsign \| default('N0CALL') }}` | role | Callsign rendered into the Selfie Station output/overlay. |
| `hamstack_selfie_station_event_name` | string | `{{ hamstack_event_name \| default('') }}` | role | Event name rendered into the output/overlay when desired. |
| `hamstack_selfie_station_camera_device` | resource name | `""` | role | Camera from hamstack_devices. |
| `hamstack_selfie_station_trigger_device` | resource name | `""` | role | Trigger/HID device from hamstack_devices. |
| `hamstack_selfie_station_radio` | resource name | `""` | role | Radio from hamstack_radios used for the transmit handoff when local. |
| `hamstack_selfie_station_interface` | resource name | `""` | role | Device from hamstack_devices used for audio/PTT when needed. |
| `hamstack_selfie_station_overlay_template` | string | `de {{ hamstack_callsign \| default('N0CALL') }}` | role | Text/template used to build the image overlay. |
| `hamstack_selfie_station_image_dir` | path/string | `{{ (hamstack_data_dir \| default('/var/lib/hamstack')) ~ '/selfie_station' }}` | role | Directory for captured/generated images. |
| `hamstack_selfie_station_transmit_enabled` | boolean | `false` | role | Allow the workflow to key the configured interface and transmit generated SSTV audio. New deployments begin in dry-run mode. |
| `hamstack_selfie_station_sstv_mode` | string | `""` | role | SSTV mode used for transmission. Empty means use the supported application/default configuration. |
| `hamstack_selfie_station_sstv_target` | string | `local` | role | Target SSTV endpoint or integration mode, such as local or a named future remote endpoint. |
| `hamstack_selfie_station_autostart` | boolean | `true` | role | Start the Selfie Station service automatically. |
| `hamstack_selfie_station_sample_rate` | integer | `48000` | role | Generated/transmitted audio sample rate. |
| `hamstack_selfie_station_cw_enabled` | boolean | `true` | role | Prefix SSTV audio with the software-generated CW station identifier. |
| `hamstack_selfie_station_cw_wpm` | integer | `15` | role | CW identifier speed in words per minute. |
| `hamstack_selfie_station_cw_tone_hz` | number | `700.0` | role | CW identifier tone frequency. |
| `hamstack_selfie_station_ptt_lead_seconds` | number | `0.30` | role | Delay after keying PTT before audio playback. |
| `hamstack_selfie_station_ptt_tail_seconds` | number | `0.20` | role | Delay after playback before unkeying PTT. |
| `hamstack_selfie_station_trigger_key` | string | `KEY_B` | role | Linux input-event key emitted by the trigger device. |
| `hamstack_selfie_station_trigger_fallback_device` | path | `/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd` | role | Fallback foot-pedal event device when no HID endpoint is supplied. |
| `hamstack_selfie_station_camera_width` | integer | `1640` | role | Camera still-capture width. |
| `hamstack_selfie_station_camera_height` | integer | `1232` | role | Camera still-capture height. |
| `hamstack_selfie_station_extra_settings` | dictionary | `{}` | role | Selfie Station settings not yet promoted to first-class variables. |

The Selfie Station should normally reference shared `camera`, `hid`, radio, and interface resources from `hamstack_devices` / `hamstack_radios`; it does not own those devices.

<a id="role-sstv-rx"></a>
#### `sstv-rx`

Receive-only SSTV appliance built around an RTL-SDR, GQRX, and the
HamRadioVillage QSSTV fork. GQRX remains the operator-facing tuner/waterfall so
QSY and gain changes do not require an Ansible run. HamStack seeds a private
first-run profile and routes GQRX audio through a named PulseAudio or
PipeWire-Pulse sink into QSSTV.

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_sstv_rx_enabled` | boolean | `false` | role | Enable the receive-only SSTV appliance. |
| `hamstack_sstv_rx_install` | boolean | `true` | role | Install GQRX, RTL-SDR tooling, PulseAudio client tools, VOLK tools, and the shared HRV QSSTV runtime. |
| `hamstack_sstv_rx_backend` | string | `qsstv` | role | SSTV decoder/display backend. The supported backend is the HRV QSSTV build. |
| `hamstack_sstv_rx_sdr_backend` | string | `gqrx` | role | SDR receiver/tuner backend. The current appliance implementation uses GQRX. |
| `hamstack_sstv_rx_user` | user/string | `hamstack_operator_user` | role | Desktop account that runs GQRX and QSSTV. |
| `hamstack_sstv_rx_callsign` | string | site callsign | role | Station callsign available to the SSTV workflow. |
| `hamstack_sstv_rx_frequency_mhz` | number/null | `null` | role | Initial GQRX receive frequency. Required when the role is enabled; later operator QSY state is preserved. |
| `hamstack_sstv_rx_gqrx_device` | string | `rtl=0` | role | GQRX device string used when seeding a new appliance profile. |
| `hamstack_sstv_rx_gqrx_sample_rate` | integer | `2400000` | role | Initial GQRX SDR sample rate. |
| `hamstack_sstv_rx_gqrx_demod` | string | `Narrow FM` | role | Initial GQRX demodulation mode. |
| `hamstack_sstv_rx_gqrx_autostart` | boolean | `true` | role | Autostart GQRX in the selected desktop session. |
| `hamstack_sstv_rx_qsstv_autostart` | boolean | `true` | role | Autostart QSSTV in the selected desktop session. |
| `hamstack_sstv_rx_pulse_sink` | string | `hamstack_sstv` | role | Named Pulse/PipeWire-Pulse sink used to route GQRX audio into QSSTV. |
| `hamstack_sstv_rx_image_dir` | path/string | `<hamstack_data_dir>/sstv-rx` | role | Directory used for received SSTV images. |
| `hamstack_sstv_rx_blacklist_dvb` | boolean | `false` | role | Optionally blacklist DVB RTL2832 drivers on a dedicated SDR appliance. |
| `hamstack_sstv_rx_extra_settings` | dictionary | `{}` | role | Reserved SSTV RX settings not yet promoted to first-class variables. |

The role seeds GQRX/QSSTV configuration only when it does not already exist, so
normal operator tuning changes survive later convergence. The internal
`digital/qsstv-runtime` support role builds the HamRadioVillage QSSTV source and
exposes it as `/usr/local/bin/qsstv`; it is not enabled directly from
`site.yml`.

<a id="role-sstv-workstation"></a>
#### `sstv-workstation`

General-purpose interactive SSTV workstation for a conventional radio/audio/PTT
station. It deliberately remains separate from both the receive-only SDR
appliance and the camera/trigger-oriented Selfie Station.

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_sstv_workstation_enabled` | boolean | `false` | role | Enable the interactive SSTV workstation. |
| `hamstack_sstv_workstation_install` | boolean | `true` | role | Build/install the shared HamRadioVillage QSSTV runtime. |
| `hamstack_sstv_workstation_backend` | string | `qsstv` | role | SSTV application backend. The supported backend is QSSTV. |
| `hamstack_sstv_workstation_user` | user/string | `hamstack_operator_user` | role | Desktop account that runs QSSTV. |
| `hamstack_sstv_workstation_callsign` | string | site callsign | role | Workstation callsign. |
| `hamstack_sstv_workstation_radio` | resource name | `""` | role | Radio from `hamstack_radios`; reserved for live radio/PTT integration. |
| `hamstack_sstv_workstation_interface` | resource name | `""` | role | Device from `hamstack_devices`; reserved for audio/PTT integration. |
| `hamstack_sstv_workstation_receive_enabled` | boolean | `true` | role | Describe/enable the workstation receive workflow. |
| `hamstack_sstv_workstation_transmit_enabled` | boolean | `false` | role | Describe/enable the transmit workflow; disabled by default. |
| `hamstack_sstv_workstation_receive_frequency_mhz` | number/null | `null` | role | Receive-frequency metadata for the station. |
| `hamstack_sstv_workstation_transmit_frequency_mhz` | number/null | `null` | role | Transmit-frequency metadata for the station. |
| `hamstack_sstv_workstation_default_mode` | string | `""` | role | Default SSTV mode; empty leaves application behavior unchanged. |
| `hamstack_sstv_workstation_image_dir` | path/string | `<hamstack_data_dir>/sstv-workstation` | role | Workstation SSTV image directory. |
| `hamstack_sstv_workstation_autostart` | boolean | `true` | role | Autostart QSSTV in the selected desktop session. |
| `hamstack_sstv_workstation_extra_settings` | dictionary | `{}` | role | Reserved workstation settings not yet promoted to first-class variables. |

Live reference-hardware RX/TX validation and detailed QSSTV audio/PTT preference
automation remain operator-owned until a portable implementation is validated.

<a id="role-slowrxd"></a>
#### `slowrxd`

Headless SSTV receive daemon built from a pinned commit of the upstream
`slowrx-daemon` branch. Receive-only; it never keys a radio.

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_slowrxd_enabled` | boolean | `false` | role | Build, install, and run slowrxd. |
| `hamstack_slowrxd_repo` | URL | `https://github.com/sjlongland/slowrx.git` | role | slowrx source repository. |
| `hamstack_slowrxd_version` | git commit | `c94327ae40ab970b0bea20ebb378d71f8e69b98a` | role | Pinned commit on the `slowrx-daemon` branch; changing it triggers a rebuild. |
| `hamstack_slowrxd_source_dir` | path | `/opt/hamstack/slowrx-source` | role | Source checkout and build tree. |
| `hamstack_slowrxd_install_path` | path | `/usr/local/bin/slowrxd` | role | Installed daemon binary. |
| `hamstack_slowrxd_hook_path` | path | `/usr/local/libexec/hamstack/slowrxd-hook` | role | Event hook script installed when a hook URL is set. |
| `hamstack_slowrxd_user` | string | `hamstack-slowrxd` | role | Unprivileged service account. |
| `hamstack_slowrxd_group` | string | `hamstack-slowrxd` | role | Primary group of the service account. |
| `hamstack_slowrxd_manage_user` | boolean | `true` | role | Create the service account/group as a nologin system user. |
| `hamstack_slowrxd_user_groups` | list[string] | `audio` | role | Supplementary groups granting ALSA capture access. |
| `hamstack_slowrxd_device` | string | `plughw:CARD=AllInOneCable,DEV=0` | role | ALSA capture PCM carrying receiver audio. |
| `hamstack_slowrxd_sample_rate` | integer | `48000` | role | Capture sample rate (slowrxd clamps above 48000). |
| `hamstack_slowrxd_channel` | string | `l` | role | Capture channel: `l`, `r`, or `m` (mono). |
| `hamstack_slowrxd_output_dir` | path | `<hamstack_data_dir>/slowrxd` | role | Directory for in-progress and final images, logs, and audio dumps. |
| `hamstack_slowrxd_hook_url` | URL | `""` | role | Endpoint that receives a JSON POST per slowrxd event; empty disables the hook. |
| `hamstack_slowrxd_audio_retention` | duration | `1d` | role | systemd-tmpfiles age for per-image `.au` audio dumps. |
| `hamstack_slowrxd_extra_args` | list[string] | `[]` | role | Additional slowrxd arguments, such as `-F` or `-S`. |
| `hamstack_slowrxd_autostart` | boolean | `true` | role | Enable and start the slowrxd service. |

<a id="role-sstv-booth"></a>
#### `sstv_booth`

Interactive booth station: shows slowrxd receptions on a local kiosk page and
sends pedal-triggered selfies as SSTV. Transmission is disabled by default.

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_sstv_booth_enabled` | boolean | `false` | role | Enable the SSTV booth service. |
| `hamstack_sstv_booth_user` | string | `hamstack-sstv-booth` | role | Dedicated unprivileged service account. |
| `hamstack_sstv_booth_group` | string | `hamstack-sstv-booth` | role | Primary group of the service account. |
| `hamstack_sstv_booth_manage_user` | boolean | `true` | role | Create the service account/group as a nologin system user. |
| `hamstack_sstv_booth_user_groups` | list[string] | `audio`, `dialout`, `video`, `input` | role | Supplementary groups for AIOC audio/serial, camera, and pedal access. |
| `hamstack_sstv_booth_install_dir` | path | `/opt/hamstack/sstv_booth` | role | Root-owned application directory. |
| `hamstack_sstv_booth_venv_dir` | path | `/opt/hamstack/sstv_booth/venv` | role | Python virtual environment (system site packages plus PySSTV). |
| `hamstack_sstv_booth_data_dir` | path | `<hamstack_data_dir>/sstv_booth` | role | Gallery, work files, and TX history. |
| `hamstack_sstv_booth_rx_dir` | path | `hamstack_slowrxd_output_dir` | role | slowrxd output directory read by the booth. |
| `hamstack_sstv_booth_listen_address` | address | `127.0.0.1` | role | HTTP listen address; keep it local to the kiosk. |
| `hamstack_sstv_booth_http_port` | integer | `8454` | role | HTTP listener for the kiosk page and slowrxd hook. |
| `hamstack_sstv_booth_callsign` | string | site callsign | role | Callsign overlaid on every image and sent as the CW ID. |
| `hamstack_sstv_booth_sstv_mode` | string | `Robot36` | role | Transmit mode: `Robot36`, `MartinM1`, or `ScottieS1`. |
| `hamstack_sstv_booth_blurb_mode` | string | `fixed` | role | Top overlay line: `fixed`, `random`, or `none`. |
| `hamstack_sstv_booth_blurb_text` | string | `hamstack_event_name` | role | Text used by `fixed` blurb mode. |
| `hamstack_sstv_booth_blurb_list` | list[string] | `[]` | role | Candidates for `random` blurb mode. |
| `hamstack_sstv_booth_tx_enabled` | boolean | `false` | role | Key the AIOC and transmit. When false, selfies run as on-screen dry runs. |
| `hamstack_sstv_booth_tx_cooldown_s` | number | `60` | role | Minimum seconds between the end of one transmission and the next selfie. |
| `hamstack_sstv_booth_max_tx_per_hour` | integer | `20` | role | Sliding one-hour cap on transmissions, persisted across restarts. |
| `hamstack_sstv_booth_rx_ignore_tail_s` | number | `3` | role | Seconds after the booth's own TX during which receive events are ignored. |
| `hamstack_sstv_booth_countdown_s` | number | `5` | role | Countdown over the live preview before capture. |
| `hamstack_sstv_booth_review_s` | number | `3` | role | Review time during which the pedal cancels the transmission. |
| `hamstack_sstv_booth_interface` | resource name | `""` | role | AIOC device from `hamstack_devices` (`serial` and `audio_playback` endpoints); empty auto-detects. |
| `hamstack_sstv_booth_trigger_device` | resource name | `""` | role | Pedal device from `hamstack_devices` (`hid` endpoint). |
| `hamstack_sstv_booth_trigger_key` | string | `KEY_B` | role | Linux input-event key emitted by the pedal. |
| `hamstack_sstv_booth_trigger_fallback_device` | path | `/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd` | role | Pedal event device used when no `hid` endpoint is supplied. |
| `hamstack_sstv_booth_sample_rate` | integer | `48000` | role | Generated/transmitted audio sample rate. |
| `hamstack_sstv_booth_cw_enabled` | boolean | `true` | role | Prefix transmissions with a software-generated CW callsign ID. |
| `hamstack_sstv_booth_cw_wpm` | integer | `15` | role | CW ID speed. |
| `hamstack_sstv_booth_cw_tone_hz` | number | `700.0` | role | CW ID tone frequency. |
| `hamstack_sstv_booth_ptt_lead_seconds` | number | `0.30` | role | Delay after keying PTT before audio playback. |
| `hamstack_sstv_booth_ptt_tail_seconds` | number | `0.20` | role | Delay after playback before unkeying PTT. |
| `hamstack_sstv_booth_camera_width` | integer | `1280` | role | Capture stream width. |
| `hamstack_sstv_booth_camera_height` | integer | `720` | role | Capture stream height. |
| `hamstack_sstv_booth_autostart` | boolean | `true` | role | Enable and start the booth service. |

The booth references shared AIOC and pedal resources from `hamstack_devices`; it
does not own those devices. It does not set radio frequencies.

<a id="role-morse-keyer"></a>
#### `morse-keyer`

Deploys the HamRadioVillage morse-keyer GPIO bridge (bundled in the role), which turns a Morse key,
paddles, or keyer output on Raspberry Pi GPIO into key presses on a virtual
keyboard for browser trainers such as hamvillage.org/morse-trainer. Nothing is
transmitted.

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_morse_keyer_enabled` | boolean | `false` | role | Install and run the Morse keyer bridge. |
| `hamstack_morse_keyer_install_dir` | path | `/opt/hamstack/morse-keyer` | role | Root-owned directory for the bundled `morse_keyer.py`. |
| `hamstack_morse_keyer_user` | string | `hamstack-morse-keyer` | role | Unprivileged service account. |
| `hamstack_morse_keyer_group` | string | `hamstack-morse-keyer` | role | Primary group of the service account. |
| `hamstack_morse_keyer_manage_user` | boolean | `true` | role | Create the service account/group as a nologin system user. |
| `hamstack_morse_keyer_user_groups` | list[string] | `input`, `gpio` | role | Supplementary groups for `/dev/uinput` and GPIO access. |
| `hamstack_morse_keyer_mode` | string | `straight` | role | `straight` (key or keyer output passed through) or `iambic` (paddles keyed by an on-Pi Curtis B keyer). |
| `hamstack_morse_keyer_gpio` | integer | `17` | role | BCM GPIO for the straight key or dit paddle (tip). |
| `hamstack_morse_keyer_dah_gpio` | integer | `27` | role | BCM GPIO for the dah paddle (ring); used only in `iambic` mode. |
| `hamstack_morse_keyer_key` | string | `KEY_SPACE` | role | evdev key name pressed on the virtual keyboard. |
| `hamstack_morse_keyer_bounce_ms` | number | `3` | role | Contact debounce applied to both edges (0-15 ms). |
| `hamstack_morse_keyer_wpm` | number | `20` | role | Iambic keyer speed; keep near the trainer's speed. |
| `hamstack_morse_keyer_boot_config` | path | `/boot/firmware/config.txt` | role | Boot configuration checked for conflicting `gpio-key` overlays. |
| `hamstack_morse_keyer_autorepeat_user` | user/string | `hamstack_operator_user` | role | Desktop account whose X11 session gets auto-repeat turned off for the key; empty skips it. |
| `hamstack_morse_keyer_x11_keycode` | integer | `65` | role | X11 keycode of the emitted key (evdev code + 8; 65 is Space). |
| `hamstack_morse_keyer_autostart` | boolean | `true` | role | Enable and start the bridge service. |


### Voice

<a id="role-allstar"></a>
#### `allstar`

The AllStar role manages a preinstalled ASL3 node. The generated variable
reference lists the full current surface; the core baseline is:

```yaml
hamstack_allstar_enabled: true
hamstack_allstar_callsign: N0CALL
hamstack_allstar_node_number: 123456
hamstack_allstar_duplex: 1

hamstack_allstar_channel_driver: simpleusb
hamstack_allstar_register: true
```

`simpleusb` is the reference path and exposes conservative COR/CTCSS/PTT
defaults plus optional calibrated audio levels. `usbradio` is supported through
a native settings dictionary, while `hub` selects `dahdi/pseudo`.

Public registration is opt-in and uses
`vault_hamstack_allstar_node_password`. HamStack edits ASL3's native templated
configuration; it does not install or image AllStarLink.

<a id="role-wpsd"></a>
#### `wpsd`

The WPSD role manages a pre-imaged, booted WPSD appliance. Core variables are:

```yaml
hamstack_wpsd_enabled: true
hamstack_wpsd_callsign: N0CALL
hamstack_wpsd_modem: "EXACT-WPSD-MODEM-ID"
hamstack_wpsd_frequency_mhz: 446.500
hamstack_wpsd_modes:
  - dmr
```

For duplex systems, use `hamstack_wpsd_rx_frequency_mhz` and
`hamstack_wpsd_tx_frequency_mhz` separately.

HamStack owns the stable baseline: identity, modem selection, simplex/duplex,
frequency/location, basic mode enable flags, and optional modem offsets. It can
also opt in to one reproducible DMRGateway custom master with explicit routing
rules (for example HRV URF478/TG 4001). Its master password must be stored as
`vault_hamstack_wpsd_dmr_custom_network_password` in encrypted Vault data.
BrandMeister/TGIF account management,
arbitrary multi-network policy, hostfile management, dashboard credentials, and
profiles remain WPSD operator configuration.

`hamstack_wpsd_config_backups` (default `false`) controls whether Ansible
leaves `*~` backup copies of the WPSD files it edits; those files carry network
credentials, so backups are off unless deliberately enabled.

See `docs/variables.md` for the exhaustive generated variable index.

## Secret variables

The following variable names are reserved for encrypted local Vault data. They are intentionally absent from role defaults so a missing secret is distinguishable from an empty credential.

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `vault_hamstack_44connect_private_key` | string | `null` | secret | WireGuard private key issued/generated for the 44Net Connect tunnel. |
| `vault_hamstack_44connect_preshared_key` | string | `null` | secret | Optional WireGuard preshared key for the 44Net peer. |
| `vault_hamstack_routeros_password` | string | `null` | secret | RouterOS API/API-SSL credential for the network-device backend. |
| `vault_hamstack_graywolf_password` | string | `null` | secret | Graywolf web/API management password. |
| `vault_hamstack_aprs_graywolf_password` | string | `null` | secret | Compatibility fallback for older APRS/Graywolf inventories; prefer `vault_hamstack_graywolf_password`. |
| `vault_hamstack_linbpq_telnet_users` | list[dictionary] | `[]` | secret | LinBPQ Telnet/Web user records including passwords and SYSOP flags. |
| `vault_hamstack_winlink_password` | string | `null` | secret | Winlink account password when required by the selected implementation. |
| `vault_hamstack_cloudlog_database_password` | string | `null` | secret | Cloudlog database password for managed deployments. |
| `vault_hamstack_dcdash_admin_password` | string | `null` | secret | DCDash administrative password written to its protected environment file. |
| `vault_hamstack_wavelog_database_password` | string | `null` | secret | Wavelog database password for managed deployments. |
| `vault_hamstack_technitium_admin_password` | string | `null` | secret | Technitium DNS administrative password used for managed API/bootstrap operations. |
| `vault_hamstack_allstar_node_password` | string | `null` | secret | AllStar node/service credential when required by the supported configuration. |
| `vault_hamstack_wpsd_dmr_custom_network_password` | string | `null` | secret | Password for the opt-in WPSD DMRGateway custom master. |

## Adding new variables

Role authors should prefer an existing global concept or shared resource before inventing a new variable. New public variables should:

- use the `hamstack_` prefix, or `vault_hamstack_` for secrets;
- be documented here;
- have a safe default in the role's `defaults/main.yml` when a default is meaningful;
- describe HamStack intent rather than blindly mirror every upstream configuration knob;
- avoid embedding hardware details inside an application role when the same physical resource can be shared by multiple roles.

Complex upstream-specific settings may initially live in the role's `*_extra_settings` dictionary. If a setting becomes common, important, or cross-role, promote it to a documented first-class variable in a later schema revision.

### LinBPQ derived identity

LinBPQ can use complete callsigns or derive them from the site callsign and
role-specific SSIDs.

```yaml
hamstack_callsign: N0CALL

hamstack_linbpq_node_ssid: 7
hamstack_linbpq_node_alias: NODE

hamstack_linbpq_bbs_enabled: true
hamstack_linbpq_bbs_ssid: 1
hamstack_linbpq_bbs_alias: BBS
```

`hamstack_linbpq_port_defaults` contains shared KISS/AX.25 timing defaults.
Items in `hamstack_linbpq_ports` override only the settings that differ for a
specific RF channel. IP-service ports, prompts, BBS application number/command,
and node behavior are variables as well.

The model was informed by a multi-band conference deployment, but no event
callsign, SSID, frequency, alias, or KISS port is required by HamStack.

## Network-device inventory

Routers and network appliances are intentionally outside the normal Linux-node
inventory. Store them in `inventory/local/network.yml` and apply them through
`playbooks/network.yml`.

Common inventory identity fields are:

| Variable | Type | Default | Scope | Purpose |
| --- | --- | --- | --- | --- |
| `hamstack_network_platform` | string | none | network device | Backend selector: `openwrt` or `routeros`. |
| `hamstack_network_vendor` | string | empty | network device | Vendor/family metadata such as `glinet` or `mikrotik`. |
| `hamstack_network_model` | string | empty | network device | Human-readable model. |
| `hamstack_network_hostname` | string | empty | network device | Desired platform hostname. |
| `hamstack_network_lans` | list | `[]` | network device | Common interface/address definitions; OpenWrt also consumes optional DHCP settings. |
| `hamstack_network_wifi` | list | `[]` | network device | OpenWrt SSID/security definitions; RouterOS currently uses native-path escape hatches for Wi-Fi. |
| `hamstack_network_routes` | list | `[]` | network device | Static routes translated by both supported network backends. |
| `hamstack_network_firewall_zones` | list | `[]` | network device | OpenWrt simple firewall-zone definitions; RouterOS firewall remains a native-path configuration surface. |

See [network-devices.md](network-devices.md).

## Service-node sprint roles

The exhaustive variable list is generated in `docs/variables.md`. The following
summarizes the automation boundary for the newer service roles.

- `services/gatus` deploys Gatus and can derive basic health checks from the
  HamStack inventory; `hamstack_gatus_endpoints` accepts additional native
  endpoint definitions. Set the inventory-only per-host variable
  `hamstack_gatus_monitor_node: false` on a node to omit its automatic ICMP
  reachability check. The variable defaults to `true` when absent.
- `services/dcdash` deploys a selected DCDash git ref and requires
  `vault_hamstack_dcdash_admin_password`.
- `services/blur-deck` manages ReadyMedia/MiniDLNA and an operator-supplied
  media directory; it does not render the deck.
- `services/conham-display` mirrors the rendered CONHAM site transactionally and
  serves the last successful mirror locally over HTTPS.
- `services/meshtastic-dashboard` hosts the official Meshtastic Web client.
- `services/cloudlog` installs the native Apache/PHP/MariaDB stack and then
  leaves Cloudlog's own installer/workflow to Cloudlog.
- `services/wavelog` installs the upstream-recommended Docker/MariaDB stack and
  leaves Wavelog's own installer/workflow to Wavelog.

Logging-provider synchronization/reconciliation is intentionally outside
HamStack's automation layer.

## Desktop and infrastructure roles

HamStack distinguishes operator-facing workstations from service applications
and network appliances.

### Desktop

- `desktop/hamstack-dev` prepares a Debian-family development environment from
  an already-provided HamStack source tree.
- `desktop/hamstack-controller` prepares a lean conference control station for
  running Ansible playbooks.
- `desktop/kiosk` launches a configurable Chromium kiosk. `hamstack_kiosk_urls`
  opens several pages as tabs, and `hamstack_kiosk_rotate_interval_s` rotates
  them with `xdotool` (X11 only), pausing for `hamstack_kiosk_rotate_idle_hold_s`
  after local keyboard or mouse input. `hamstack_kiosk_force_x11` switches a
  Raspberry Pi OS desktop to X11 with `raspi-config` and reports that a reboot is
  needed.
- `desktop/chirp` installs CHIRP-next for radio programming;
  `hamstack_chirp_wheel_checksum` verifies the wheel path.
- `desktop/netlogger` installs an operator-supplied NetLogger Debian package;
  `hamstack_netlogger_package_checksum` verifies a URL-sourced package.

### Infrastructure

- `infrastructure/technitium-dns` deploys Technitium DNS with the default local
  namespace `hamstack.home.arpa`, configurable forwarding, and no DHCP.
- `infrastructure/netboot` serves an HTTP/iPXE menu without running DHCP or TFTP.

See [profiles.md](profiles.md) for deployment compositions and
[variables.md](variables.md) for the exhaustive generated variable index.

### Additional digital/packet capabilities

The current role set also includes `digital/multimon-ng`, `digital/unipager`,
`digital/js8call`, `digital/ft8web`, and a Pat-backed `packet/winlink` role.
The managed multimon-ng service runs as the dedicated
`hamstack_multimon_ng_user` account, and JS8Call AppImages are verified
against `hamstack_js8call_x86_64_checksum` / `hamstack_js8call_aarch64_checksum`.
Downloaded packages and executables must come from HTTPS URLs.
AREDN integration is read-only monitoring of existing AREDN nodes rather than
firmware/configuration ownership.
