# `morse-keyer` role

> **Status:** implemented HamRadioVillage morse-keyer GPIO bridge; not yet hardware validated.

## Purpose

Let visitors key a browser Morse trainer such as
<https://hamvillage.org/morse-trainer> with a real key, paddles, or a keyer's
output. The role deploys the bridge from
[HamRadioVillage/morse-keyer](https://github.com/HamRadioVillage/morse-keyer),
which reads a key on Raspberry Pi GPIO and presses a key (Space by default) on a
virtual keyboard through `/dev/uinput`. Nothing is transmitted.

## Expected starting state

Raspberry Pi OS (Debian-family) on a Raspberry Pi with a desktop session for
the trainer, normally `desktop/kiosk`.

## Wiring

Connect the key to the 40-pin GPIO header through a 3.5 mm TRS breakout jack:

| Breakout contact | Straight key / keyer output | Paddles (`iambic`) | Raspberry Pi header |
| --- | --- | --- | --- |
| Tip | key | dit | GPIO17 (physical pin 11) |
| Ring | — | dah (optional) | GPIO27 (physical pin 13) |
| Sleeve | common | common | GND (physical pin 9) |

**Do not plug the key into the Pi's onboard 3.5 mm audio/video jack.** That
jack is output-only (stereo audio plus composite video) and is not connected to
any header GPIO, so a key there can never be read. It can still carry sidetone
audio out.

**Never connect the key to 3.3 V or 5 V.** The key only shorts a GPIO to
ground. The GPIOs use the SoC's internal pull-ups, so an open contact reads
high (key up) and a closed contact, or a keyer's transistor output pulling the
line to ground, reads low (key down). No external resistors are needed.

The key pins are set with `hamstack_morse_keyer_gpio` (default 17) and, for
paddles, `hamstack_morse_keyer_dah_gpio` (default 27). Contact debounce is
applied equally to press and release (`hamstack_morse_keyer_bounce_ms`, default
5 ms). Much longer debounce clips fast CW: a dit at 20 WPM is 60 ms.

A mono (TS) plug in a stereo breakout jack shorts the ring to the sleeve, which
is harmless in `straight` mode (the ring is never read) but sends continuous
dahs in `iambic` mode.

## Modes

- **`straight`** (default): a passthrough. Contact closed is key down, open is
  key up; the trainer times the press to tell dits from dahs.
- **`iambic`**: a Curtis B keyer runs on the Pi and sends correctly timed
  presses. Keep `hamstack_morse_keyer_wpm` near the trainer's own speed
  (20 WPM): the trainer decides dit or dah by press length, so a much slower
  keyer speed decodes wrongly.

## Responsibilities

- Install the bundled `morse_keyer.py` into `hamstack_morse_keyer_install_dir`
  (root-owned) and the `99-morse-keyer.rules` udev rule, which gives the
  `input` group access to `/dev/uinput`.
- Load `uinput` at boot and run `morse_keyer.py` as the unprivileged
  `hamstack-morse-keyer` account (groups `input`, `gpio`) under
  `hamstack-morse-keyer.service`.
- Refuse to run while a `dtoverlay=gpio-key` line in the boot configuration
  claims the same GPIO, because the kernel driver would hold the pin.
- Turn off X11 auto-repeat for the emitted key at login for
  `hamstack_morse_keyer_autorepeat_user` (`xset -r 65` for Space). Without it,
  holding a long dah makes the desktop send repeated key presses. Wayland
  sessions ignore `xset`; use an X11 session (see `desktop/kiosk`).

HamStack renders the program, udev rule, service unit, `modules-load.d` entry,
and autostart entry authoritatively.

## Provenance

`files/morse_keyer.py` and `files/99-morse-keyer.rules` are copied unmodified
from HamRadioVillage/morse-keyer at commit
`f57d95c982b0328ba7be38a470616688d979aeb7`, with the permission of
HamRadioVillage, and are distributed as part of HamStack under the GNU GPL v3.
Behaviour is adapted through command-line options in the service unit rather
than by editing the program. To update, copy the files from a newer upstream
commit and record that commit here.

## Configuration

See the [HamStack configuration reference](../../../docs/configuration.md#role-morse-keyer)
for the public variables owned by this role.
