# `slowrxd` role

> **Status:** implemented headless SSTV receive daemon built from a pinned upstream commit; receive audio levels remain operator-tuned.

## Purpose

Run [slowrxd](https://github.com/sjlongland/slowrx/tree/slowrx-daemon), the
headless daemon from Stuart Longland's `slowrx-daemon` branch of slowrx, as a
systemd service that decodes SSTV from an ALSA capture device into a directory
of PNG images. It is receive-only and never keys a radio.

`digital/sstv_booth` consumes its output, but the role is independently useful
for any unattended SSTV receive/archive node.

## Expected starting state

A Debian-family host with an ALSA capture device carrying receiver audio, such
as an AIOC (`plughw:CARD=AllInOneCable,DEV=0`). Internet access is needed on the
first run to clone the upstream source.

## Responsibilities

- Clone `hamstack_slowrxd_repo` at the pinned `hamstack_slowrxd_version` commit
  and build it with `make slowrxd`. A commit-stamped marker in the source tree
  keeps later runs from rebuilding until the pin changes.
- Install `/usr/local/bin/slowrxd` and run it as the unprivileged
  `hamstack-slowrxd` account (member of `audio`) with systemd hardening. The
  service can write only to `hamstack_slowrxd_output_dir`.
- Optionally install an event hook that POSTs each slowrxd event to
  `hamstack_slowrxd_hook_url`.
- Prune slowrxd's per-image `.au` audio dumps with a systemd-tmpfiles age rule.

HamStack owns the binary, `/etc/default/hamstack-slowrxd`,
`/etc/systemd/system/hamstack-slowrxd.service`,
`/etc/tmpfiles.d/hamstack-slowrxd.conf`, and the hook script; each is rendered
authoritatively. ALSA mixer/capture levels and receiver tuning remain
operator-owned.

## Output files

slowrxd writes into the output directory:

- `inprogress.png`, `inprogress.ndjson`, `inprogress.au` while an image is
  being received (the PNG is rewritten at most every 5 seconds);
- `YYYY-mm-ddTHH-MMZ-<MODE>[-<FSKID>].png` plus matching `.ndjson` and `.au`
  files once reception ends;
- `latest.png`, `latest.ndjson`, `latest.au` symlinks to the newest image.

## Event hook

When `hamstack_slowrxd_hook_url` is set, slowrxd runs
`hamstack_slowrxd_hook_path` for `VIS_DETECT`, `IMAGE_REFRESHED`, and
`RECEIVE_END`. slowrxd blocks until the hook exits, so the hook backgrounds a
`curl` POST of `{"event": "...", "image": "<basename>"}` and returns
immediately. Only the event name and the image basename are forwarded.

## Upstream behavior worth knowing

- `-I`, `-L`, and `-A` paths are resolved against `-d` only when `-d` appears
  first on the command line; the unit always passes `-d` first and leaves those
  paths at their defaults.
- Disabling audio dumps with `-A -` leaves the hook's audio argument
  uninitialised in the pinned commit, so dumps stay enabled and are pruned by
  the tmpfiles rule instead.
- The in-progress PNG is truncated and rewritten in place; readers should
  tolerate a partially written file.

## Configuration

See the [HamStack configuration reference](../../../docs/configuration.md#role-slowrxd)
for the public variables owned by this role.
