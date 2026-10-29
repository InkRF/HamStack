# `desktop/kiosk`

Generic Chromium kiosk role for HamStack display stations.

It installs Chromium and small X11 helpers, disables display blanking for the
session, optionally rotates a named display, hides the mouse cursor, and creates
an XDG autostart launcher for a configurable URL.

The role does **not** configure desktop-manager autologin. Login policy varies
between distributions/desktops and can be layered on later if a deployment
actually needs unattended login.

The kiosk is intentionally application-neutral: Gatus, CONHAM, DCDash, FT8Web,
exam software, or future presentation applications can all use the same role.

## Multiple pages and tab rotation

Set `hamstack_kiosk_urls` to open several pages as Chromium tabs (the single
`hamstack_kiosk_url` is used when the list is empty). With
`hamstack_kiosk_rotate_interval_s` greater than zero, the launcher also starts
`hamstack-kiosk-rotate`, which sends `ctrl+Tab` to Chromium with `xdotool` on
that interval. Rotation pauses while someone is using the keyboard or mouse and
resumes after `hamstack_kiosk_rotate_idle_hold_s` seconds without local input,
so a visitor using one page (for example a Morse trainer) is not switched
away mid-session.

Rotation requires an X11 session; `xdotool` cannot inject keys into a Wayland
compositor. Raspberry Pi OS on a Pi 4 or Pi 5 defaults to Wayland. Setting
`hamstack_kiosk_force_x11: true` runs `raspi-config nonint do_wayland W1` when
the LightDM session is not already X11, and reports that a reboot is required.
HamStack never reboots the host itself. On other distributions, select an X11
session manually.

Pages that need sound without a click (such as a Morse trainer sidetone) need
`--autoplay-policy=no-user-gesture-required` in `hamstack_kiosk_browser_args`.

## Display and touch rotation

`hamstack_kiosk_rotation` (`normal`, `left`, `right`, `inverted`) rotates
`hamstack_kiosk_output` with `xrandr` when the kiosk starts; find the output name
with `DISPLAY=:0 xrandr`. `xrandr` does not rotate touch input, so set
`hamstack_kiosk_touch_device` to the touchscreen's `xinput` name (see
`DISPLAY=:0 xinput list`) to apply the matching coordinate transformation at the
same time. For example, a Raspberry Pi Touch Display 2 used in landscape:

```yaml
hamstack_kiosk_output: DSI-1
hamstack_kiosk_rotation: left
hamstack_kiosk_touch_device: 10-005d Goodix Capacitive TouchScreen
```

Both settings are X11-only and are applied each time the kiosk launches.
Rotation set through a Wayland desktop's screen settings does not carry over to
an X11 session.
