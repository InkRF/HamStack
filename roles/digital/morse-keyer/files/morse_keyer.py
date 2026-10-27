#!/usr/bin/env python3
"""Bridge a Morse key on the Raspberry Pi's GPIO to a virtual keyboard.

Straight-key mode is a pure passthrough: contact closed -> SPACE down,
contact open -> SPACE up. The receiving app (hamvillage.org/morse-trainer)
discriminates dits from dahs by timing the press, so the only thing that
matters here is that both edges are reported with the same small, constant
latency. Symmetric latency cancels out of the measured duration; asymmetric
latency does not, which is why debounce is applied identically to both edges.

Iambic mode is not a passthrough. The trainer only accepts one input, so the
keyer has to run here and synthesize correctly-timed SPACE presses -- see
--wpm, which must stay close to the trainer's own 20 WPM or the durations
land on the wrong side of its dit/dah threshold.
"""

import argparse
import signal
import sys
import threading
import time

from evdev import UInput, ecodes

def dit_seconds(wpm):
    """One dit unit. The trainer shows '20 WPM (60ms)': 1200/wpm milliseconds."""
    return 1.2 / wpm


class KeyOutput:
    """A virtual keyboard exposing a single key.

    EV_REP is deliberately not advertised, so the kernel input core will not
    generate auto-repeat for a held key. Note that X11 and Wayland synthesize
    their own repeat on top of this -- see README for turning that off.
    """

    def __init__(self, keycode):
        self.keycode = keycode
        self._ui = UInput({ecodes.EV_KEY: [keycode]}, name="morse-keyer")
        self._down = False

    def down(self):
        if self._down:
            return
        self._ui.write(ecodes.EV_KEY, self.keycode, 1)
        self._ui.syn()
        self._down = True

    def up(self):
        if not self._down:
            return
        self._ui.write(ecodes.EV_KEY, self.keycode, 0)
        self._ui.syn()
        self._down = False

    def close(self):
        self.up()
        self._ui.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def sleep_until(deadline):
    """Sleep to an absolute perf_counter deadline so error does not accumulate."""
    remaining = deadline - time.perf_counter()
    if remaining > 0:
        time.sleep(remaining)


def run_straight(args, out):
    """Passthrough: mirror the key contact onto the virtual key."""
    from gpiozero import Button

    key = Button(args.gpio, pull_up=True, bounce_time=args.bounce_ms / 1000)
    key.when_pressed = out.down
    key.when_released = out.up

    print(f"straight key on BCM{args.gpio} -> {args.key} "
          f"(debounce {args.bounce_ms}ms). Ctrl-C to stop.")

    # Adopt whatever state the key is already in, in case it is held at startup.
    if key.is_pressed:
        out.down()

    signal.pause()


class IambicKeyer:
    """Curtis B iambic keyer emitting timed presses on a single output key.

    Curtis B: a paddle touched during the current element is remembered and
    that element is inserted next, even if the paddle is released before the
    current element finishes.
    """

    DIT, DAH = "dit", "dah"

    def __init__(self, out, wpm, dit_gpio, dah_gpio, bounce_ms):
        from gpiozero import Button

        self.out = out
        self.unit = dit_seconds(wpm)
        self.dit = Button(dit_gpio, pull_up=True, bounce_time=bounce_ms / 1000)
        self.dah = Button(dah_gpio, pull_up=True, bounce_time=bounce_ms / 1000)

        self._memory = None
        self._lock = threading.Lock()
        self._stop = threading.Event()

        self.dit.when_pressed = lambda: self._remember(self.DIT)
        self.dah.when_pressed = lambda: self._remember(self.DAH)

    def _remember(self, element):
        with self._lock:
            if self._memory is None:
                self._memory = element

    def _take_memory(self):
        with self._lock:
            element, self._memory = self._memory, None
            return element

    def _next_element(self, previous):
        """Memory first, then squeeze alternation, then whichever paddle is down."""
        remembered = self._take_memory()
        if remembered:
            return remembered
        if self.dit.is_pressed and self.dah.is_pressed:
            return self.DAH if previous == self.DIT else self.DIT
        if self.dit.is_pressed:
            return self.DIT
        if self.dah.is_pressed:
            return self.DAH
        return None

    def _send(self, element):
        """One element: 1 or 3 units down, then exactly 1 unit up."""
        length = self.unit if element == self.DIT else 3 * self.unit
        start = time.perf_counter()
        self.out.down()
        sleep_until(start + length)
        self.out.up()
        sleep_until(start + length + self.unit)

    def run(self):
        previous = None
        while not self._stop.is_set():
            element = self._next_element(previous)
            if element is None:
                previous = None
                time.sleep(0.001)
                continue
            self._send(element)
            previous = element

    def stop(self):
        self._stop.set()


def run_iambic(args, out):
    keyer = IambicKeyer(out, args.wpm, args.gpio, args.dah_gpio, args.bounce_ms)
    print(f"iambic paddle: dit BCM{args.gpio}, dah BCM{args.dah_gpio} -> "
          f"{args.key} at {args.wpm} WPM ({dit_seconds(args.wpm) * 1000:.0f}ms unit). "
          f"Ctrl-C to stop.")
    try:
        keyer.run()
    finally:
        keyer.stop()


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Bridge a Morse key on GPIO to a virtual keyboard key.")
    p.add_argument("--mode", choices=("straight", "iambic"), default="straight",
                   help="straight key passthrough (default) or iambic keyer")
    p.add_argument("--gpio", type=int, default=17,
                   help="BCM pin for the straight key, or the dit paddle (default: 17)")
    p.add_argument("--dah-gpio", type=int, default=27,
                   help="BCM pin for the dah paddle, iambic mode only (default: 27)")
    p.add_argument("--key", default="KEY_SPACE",
                   help="evdev key name to emit (default: KEY_SPACE)")
    p.add_argument("--bounce-ms", type=float, default=3.0,
                   help="contact debounce, applied to both edges (default: 3)")
    p.add_argument("--wpm", type=float, default=20.0,
                   help="iambic keyer speed; match the target app (default: 20)")
    args = p.parse_args(argv)

    if args.bounce_ms < 0:
        p.error("--bounce-ms cannot be negative")
    # A dit at the target speed is 1200/wpm ms; debounce must stay well under it.
    if args.bounce_ms > 15:
        p.error("--bounce-ms above 15 will start eating into dit length")
    if args.wpm <= 0:
        p.error("--wpm must be positive")
    if args.mode == "iambic" and args.gpio == args.dah_gpio:
        p.error("--gpio and --dah-gpio must differ")

    keycode = ecodes.ecodes.get(args.key)
    if keycode is None:
        p.error(f"unknown key name {args.key!r} (expected something like KEY_SPACE)")
    args.keycode = keycode

    return args


def main(argv=None):
    args = parse_args(argv)

    try:
        out = KeyOutput(args.keycode)
    except PermissionError:
        sys.exit("cannot open /dev/uinput -- see README (add yourself to the "
                 "'input' group and install the udev rule, or run with sudo)")

    with out:
        try:
            if args.mode == "straight":
                run_straight(args, out)
            else:
                run_iambic(args, out)
        except KeyboardInterrupt:
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
