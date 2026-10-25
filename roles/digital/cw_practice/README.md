# `cw_practice` role

> **Status:** implemented local CW practice page and Raspberry Pi GPIO Morse-key input; keying feel and sidetone level remain site-tuned.

## Purpose

Let visitors try Morse code at a kiosk. The role installs a self-contained CW
practice page (sidetone, iambic paddle keyer or straight key, and a live
decoder) and can wire a Morse key or paddle to Raspberry Pi GPIO so the key
appears to the browser as two keyboard keys. Nothing is transmitted.

## Expected starting state

- A Debian-family host with a browser, normally `desktop/kiosk`.
- For GPIO keying: Raspberry Pi firmware with `/boot/firmware/config.txt`.

## Page

The page is installed as static files under
`hamstack_cw_practice_install_dir` (default `/opt/hamstack/cw_practice`) and is
opened as `file:///opt/hamstack/cw_practice/index.html`, so it needs no web
server or port. `cw-config.js` carries the callsign, default key mode, speed,
sidetone pitch, and the `KeyboardEvent.code` values used for dit and dah.

- **Paddles** (`iambic`): the dit key sends dots, the dah key sends dashes, and
  squeezing both alternates (iambic keying with element memory).
- **Straight key** (`straight`): either contact keys the sidetone; dots and
  dashes are classified from the visitor's own timing, and the speed display
  adapts.

Chromium only plays the sidetone without a prior click when the kiosk runs
with `--autoplay-policy=no-user-gesture-required`.

## GPIO Morse key

With `hamstack_cw_practice_manage_gpio_key: true`, the role manages one marked
block at the end of `hamstack_cw_practice_boot_config`:

```text
[all]
dtoverlay=gpio-key,gpio=17,active_low=1,gpio_pull=up,keycode=29,label=cw-tip
dtoverlay=gpio-key,gpio=27,active_low=1,gpio_pull=up,keycode=97,label=cw-ring
```

Wire the key's 3.5 mm/6.35 mm TRS plug as:

| Plug contact | Raspberry Pi | Default key |
| --- | --- | --- |
| Tip (dit paddle / straight key) | GPIO17 (pin 11) | `KEY_LEFTCTRL` (browser `ControlLeft`) |
| Ring (dah paddle) | GPIO27 (pin 13) | `KEY_RIGHTCTRL` (browser `ControlRight`) |
| Sleeve | GND (for example pin 9 or 14) | — |

Both inputs are active low with the internal pull-up, so closing a contact to
the sleeve presses the key. Left/right Ctrl match the convention used by
common online Morse trainers; if the keycodes change, change
`hamstack_cw_practice_dit_key` and `hamstack_cw_practice_dah_key` to match.

HamStack owns only the block between its
`# BEGIN/END HamStack digital/cw_practice Morse key` markers and removes it
when GPIO keying is disabled. The overlay takes effect after a reboot, which
the role reports but never performs.

## Configuration

See the [HamStack configuration reference](../../../docs/configuration.md#role-cw-practice)
for the public variables owned by this role.
