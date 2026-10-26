#!/usr/bin/env python3
"""A lightweight fullscreen Windows keep-awake visualizer.

The program uses Windows' supported SetThreadExecutionState API.  It does not
move the mouse, synthesize key presses, or change the machine's power plan.
"""

from __future__ import annotations

import argparse
import ctypes
import math
import random
import sys
import threading
import time
from dataclasses import dataclass
from typing import Iterable

APP_NAME = "Awake Horizon"
VERSION = "6.1.2"


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def mix(first: str, second: str, amount: float) -> str:
    """Blend two #rrggbb colors."""

    amount = clamp(amount)

    def rgb(value: str) -> tuple[int, int, int]:
        value = value.lstrip("#")
        return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]

    color = tuple(
        round(a + (b - a) * amount)
        for a, b in zip(rgb(first), rgb(second))
    )
    return "#{:02x}{:02x}{:02x}".format(*color)


def duration_text(seconds: float) -> str:
    hours, remainder = divmod(max(0, int(seconds)), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def nonnegative_minutes(value: str) -> float:
    try:
        result = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("minutes must be a number") from error
    if not math.isfinite(result) or result < 0 or not math.isfinite(result * 60):
        raise argparse.ArgumentTypeError("minutes must be zero or greater")
    return result


class StayAwake:
    """Own a Windows system-and-display keep-awake request."""

    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    ES_CONTINUOUS = 0x80000000

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError(f"{APP_NAME} supports Windows only.")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._set_state = kernel32.SetThreadExecutionState
        self._set_state.argtypes = [ctypes.c_uint]
        self._set_state.restype = ctypes.c_uint
        self._owner_thread = threading.get_ident()
        self.active = False

    def _check_thread(self) -> None:
        if threading.get_ident() != self._owner_thread:
            raise RuntimeError("REQUEST_THREAD_MISMATCH")

    def refresh(self) -> None:
        self._check_thread()
        flags = (
            self.ES_CONTINUOUS
            | self.ES_SYSTEM_REQUIRED
            | self.ES_DISPLAY_REQUIRED
        )
        if not self._set_state(flags):
            raise OSError("POWER_REQUEST_FAILED")
        self.active = True

    def restore(self) -> None:
        self._check_thread()
        if not self.active:
            return
        if not self._set_state(self.ES_CONTINUOUS):
            raise OSError("POWER_REQUEST_CLEAR_FAILED")
        self.active = False

    def __enter__(self) -> "StayAwake":
        self.refresh()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        try:
            self.restore()
        except OSError:
            print("Warning: sleep-state restoration failed: POWER_REQUEST_CLEAR_FAILED", file=sys.stderr)


def enable_dpi_awareness() -> None:
    """Keep Tk geometry crisp on high-DPI Windows displays."""

    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        setter = user32.SetProcessDpiAwarenessContext
        setter.argtypes = [ctypes.c_void_p]
        setter.restype = ctypes.c_int
        if setter(ctypes.c_void_p(-4)):
            return
    except (AttributeError, OSError, TypeError):
        pass
    try:
        ctypes.WinDLL("user32", use_last_error=True).SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


@dataclass(frozen=True)
class MonitorBounds:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def contains(self, x: int, y: int) -> bool:
        return self.left <= x < self.right and self.top <= y < self.bottom

    @property
    def geometry(self) -> str:
        return f"{self.width}x{self.height}+{self.left}+{self.top}"


class _Rect(ctypes.Structure):
    _fields_ = (
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    )


def enumerate_monitors() -> tuple[MonitorBounds, ...]:
    """Return every active Windows display in stable left-to-right order."""

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    monitors: list[MonitorBounds] = []
    callback_type = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(_Rect),
        ctypes.c_ssize_t,
    )

    @callback_type
    def callback(
        _monitor: object,
        _device_context: object,
        rect_pointer: object,
        _data: object,
    ) -> int:
        rect = rect_pointer.contents
        monitors.append(
            MonitorBounds(rect.left, rect.top, rect.right, rect.bottom)
        )
        return 1

    enum_display_monitors = user32.EnumDisplayMonitors
    enum_display_monitors.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        callback_type,
        ctypes.c_ssize_t,
    ]
    enum_display_monitors.restype = ctypes.c_int
    if not enum_display_monitors(None, None, callback, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    if not monitors:
        raise RuntimeError("Windows did not report an active monitor.")
    return tuple(sorted(monitors, key=lambda item: (item.left, item.top)))


THEMES = {
    "cyan": ("#39e7ff", "#8cf5ff", "#6c63ff"),
    "emerald": ("#4fffb0", "#b5ffda", "#27b7a8"),
    "magenta": ("#d66bff", "#f2c5ff", "#ff4d9d"),
    "amber": ("#ffca58", "#ffe5a3", "#ff6b5f"),
}

# background stars, neural nodes, firing pulses, aurora sample points
QUALITY = {
    "low": (32, 42, 14, 22),
    "balanced": (48, 63, 24, 28),
    "high": (70, 84, 38, 34),
}


@dataclass(frozen=True)
class Star:
    x: float
    y: float
    size: float
    phase: float
    speed: float


@dataclass(frozen=True)
class NeuralNode:
    x: float
    y: float
    layer: int
    size: float
    phase: float
    speed: float


@dataclass(frozen=True)
class NeuralEdge:
    source: int
    target: int
    phase: float


@dataclass(frozen=True)
class SignalPulse:
    edge: int
    phase: float
    speed: float
    size: float


class AwakeApp:
    BG = "#050810"
    PANEL = "#0a1120"
    GRID = "#102138"
    TEXT = "#eefbff"
    MUTED = "#7892aa"

    def __init__(
        self,
        root: object,
        request: StayAwake,
        *,
        quality: str,
        theme: str,
        fps: int,
        fullscreen: bool,
        minutes: float,
        smoke_test: bool = False,
    ) -> None:
        import tkinter as tk

        self.tk = tk
        self.root = root
        self.request = request
        self.accent, self.hot, self.secondary = THEMES[theme]
        self.fps = fps
        self.frame_ms = max(16, round(1000 / fps))
        self.started = time.monotonic()
        self.deadline = self.started + minutes * 60 if minutes else None
        self.fullscreen = False
        self.windowed_geometry: str | None = None
        self.windowed_topmost = False
        self.fullscreen_monitor: MonitorBounds | None = None
        self.running = True
        self.failure_code: str | None = None
        self.frame_number = 0
        self.last_frame = self.started
        self.next_awake_refresh = self.started + 20.0
        self.next_text_refresh = 0.0
        self.layout_dirty = True
        self.width = 1100
        self.height = 680

        if quality == "auto":
            pixels = root.winfo_screenwidth() * root.winfo_screenheight()
            quality = "high" if pixels >= 3_000_000 else "balanced"
        self.quality = quality
        star_count, node_count, pulse_count, self.wave_points = QUALITY[quality]

        root.title(f"{APP_NAME} {VERSION}")
        root.configure(background=self.BG)
        root.minsize(720, 480)
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = min(1180, max(720, screen_width - 140))
        window_height = min(760, max(480, screen_height - 120))
        root.geometry(
            f"{window_width}x{window_height}"
            f"+{max(0, (screen_width - window_width) // 2)}"
            f"+{max(0, (screen_height - window_height) // 2)}"
        )
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.canvas = tk.Canvas(
            root,
            background=self.BG,
            highlightthickness=0,
            borderwidth=0,
            takefocus=True,
        )
        self.canvas.pack(fill="both", expand=True)

        self.rng = random.Random(0xA7A1E)
        self.stars = tuple(
            Star(
                self.rng.random(),
                self.rng.random(),
                self.rng.uniform(0.55, 1.8),
                self.rng.uniform(0.0, math.tau),
                self.rng.uniform(0.35, 1.25),
            )
            for _ in range(star_count)
        )
        self.nodes = self._build_neural_nodes(node_count)
        self.edges = self._build_neural_edges()
        self.pulses = tuple(
            SignalPulse(
                edge=self.rng.randrange(len(self.edges)),
                phase=self.rng.random(),
                speed=self.rng.uniform(0.10, 0.24),
                size=self.rng.uniform(1.6, 2.9),
            )
            for _ in range(pulse_count)
        )
        self.node_positions: list[tuple[float, float]] = []

        self._build_scene()
        self._bind_events()

        root.update_idletasks()
        if fullscreen and not smoke_test:
            root.after_idle(lambda: self.set_fullscreen(True))
        self.after_id = root.after(0, self._tick)

    def _build_neural_nodes(self, node_count: int) -> tuple[NeuralNode, ...]:
        """Create a deterministic seven-layer feed-forward neural field."""

        layer_count = 7
        counts = [node_count // layer_count] * layer_count
        for index in range(node_count % layer_count):
            counts[index + (layer_count - node_count % layer_count) // 2] += 1

        nodes: list[NeuralNode] = []
        for layer, count in enumerate(counts):
            for slot in range(count):
                nodes.append(
                    NeuralNode(
                        x=0.09 + 0.82 * layer / (layer_count - 1)
                        + self.rng.uniform(-0.009, 0.009),
                        y=0.11 + 0.78 * (slot + 1) / (count + 1)
                        + self.rng.uniform(-0.018, 0.018),
                        layer=layer,
                        size=self.rng.uniform(0.78, 1.35),
                        phase=self.rng.uniform(0.0, math.tau),
                        speed=self.rng.uniform(0.07, 0.19),
                    )
                )
        return tuple(nodes)

    def _build_neural_edges(self) -> tuple[NeuralEdge, ...]:
        """Wire nearby neurons forward, with a few residual connections."""

        by_layer = {
            layer: [index for index, node in enumerate(self.nodes) if node.layer == layer]
            for layer in range(7)
        }
        edges: list[NeuralEdge] = []
        seen: set[tuple[int, int]] = set()

        def connect(source: int, target: int) -> None:
            key = (source, target)
            if key in seen:
                return
            seen.add(key)
            edges.append(
                NeuralEdge(source, target, self.rng.uniform(0.0, math.tau))
            )

        for layer in range(6):
            targets = by_layer[layer + 1]
            for source in by_layer[layer]:
                nearest = sorted(
                    targets,
                    key=lambda target: abs(self.nodes[source].y - self.nodes[target].y),
                )
                connect(source, nearest[0])
                connect(source, nearest[1])
                if self.rng.random() < 0.42:
                    connect(source, self.rng.choice(targets))

        for layer in range(5):
            targets = by_layer[layer + 2]
            for source in by_layer[layer]:
                if self.rng.random() < 0.22:
                    target = min(
                        targets,
                        key=lambda item: abs(self.nodes[source].y - self.nodes[item].y),
                    )
                    connect(source, target)
        return tuple(edges)

    def _build_scene(self) -> None:
        c = self.canvas
        self.grid_lines = [
            c.create_line(0, 0, 0, 0, fill=self.GRID, width=1)
            for _ in range(12)
        ]
        self.star_items = [
            c.create_oval(0, 0, 1, 1, fill=self.MUTED, outline="")
            for _ in self.stars
        ]
        self.aurora_glows = [
            c.create_line(
                0, 0, 1, 1, fill=mix(self.BG, color, 0.12), width=18,
                smooth=True, splinesteps=8,
            )
            for color in (self.accent, self.secondary, self.accent)
        ]
        self.aurora_lines = [
            c.create_line(
                0, 0, 1, 1, fill=color, width=2,
                smooth=True, splinesteps=8,
            )
            for color in (self.accent, self.secondary, self.hot)
        ]
        self.edge_items = [
            c.create_line(
                0, 0, 0, 0,
                fill=mix(self.BG, self.accent, 0.19),
                width=1,
            )
            for _ in self.edges
        ]
        self.node_glows = [
            c.create_oval(
                0, 0, 1, 1,
                fill=mix(self.BG, self.accent, 0.20),
                outline="",
            )
            for _ in self.nodes
        ]
        self.node_items = [
            c.create_oval(
                0, 0, 1, 1,
                fill=mix(self.BG, self.accent, 0.62),
                outline=self.accent,
                width=1,
            )
            for _ in self.nodes
        ]
        self.pulse_glows = [
            c.create_oval(
                0, 0, 1, 1,
                fill=mix(self.BG, self.hot, 0.34),
                outline="",
            )
            for _ in self.pulses
        ]
        self.pulse_items = [
            c.create_oval(0, 0, 1, 1, fill=self.hot, outline="")
            for _ in self.pulses
        ]
        self.hint = c.create_text(
            0,
            0,
            text="M  NEXT MONITOR    F11  FULLSCREEN    N  WINDOWED    CTRL+Q  EXIT",
            fill=mix(self.BG, self.MUTED, 0.48),
            font=("Segoe UI", 8),
            anchor="se",
        )

    def _bind_events(self) -> None:
        self.root.bind("<Configure>", self._on_configure)
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.leave_fullscreen)
        self.root.bind_all("<Key-n>", self.leave_fullscreen)
        self.root.bind_all("<Key-N>", self.leave_fullscreen)
        self.root.bind_all("<Key-m>", self.switch_monitor)
        self.root.bind_all("<Key-M>", self.switch_monitor)
        self.root.bind("<Control-q>", self.close)
        self.root.bind("<Control-Q>", self.close)
        self.canvas.bind("<Double-Button-1>", self.toggle_fullscreen)

    def _on_configure(self, event: object) -> None:
        if getattr(event, "widget", None) is self.root:
            self.layout_dirty = True

    def set_fullscreen(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self.fullscreen:
            return
        if enabled:
            self.root.update_idletasks()
            try:
                monitors = enumerate_monitors()
            except (OSError, RuntimeError):
                self.root.bell()
                return
            monitor = self._monitor_for_window(monitors)
            self.windowed_geometry = self.root.geometry()
            self.windowed_topmost = bool(self.root.attributes("-topmost"))
            self.root.attributes("-fullscreen", False)
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
            self.root.geometry(monitor.geometry)
            self.root.update_idletasks()
            self.root.lift()
            self.fullscreen_monitor = monitor
        else:
            self.root.attributes("-fullscreen", False)
            self.root.attributes("-topmost", False)
            self.root.overrideredirect(False)
            self.root.update_idletasks()
            if self.windowed_geometry:
                self.root.geometry(self.windowed_geometry)
            self.root.attributes("-topmost", self.windowed_topmost)
            self.fullscreen_monitor = None
        self.fullscreen = enabled
        self.canvas.configure(cursor="none" if self.fullscreen else "")
        self.canvas.itemconfigure(
            self.hint,
            state="hidden" if self.fullscreen else "normal",
        )
        self.root.after_idle(self._focus_canvas)

    def _monitor_for_window(
        self,
        monitors: tuple[MonitorBounds, ...],
    ) -> MonitorBounds:
        if self.fullscreen_monitor is not None:
            for monitor in monitors:
                if monitor == self.fullscreen_monitor:
                    return monitor
        center_x = self.root.winfo_rootx() + self.root.winfo_width() // 2
        center_y = self.root.winfo_rooty() + self.root.winfo_height() // 2
        for monitor in monitors:
            if monitor.contains(center_x, center_y):
                return monitor
        return min(
            monitors,
            key=lambda item: (
                (item.left + item.width / 2 - center_x) ** 2
                + (item.top + item.height / 2 - center_y) ** 2
            ),
        )

    @staticmethod
    def _centered_geometry(
        monitor: MonitorBounds,
        width: int,
        height: int,
    ) -> str:
        width = min(max(720, width), max(720, monitor.width - 80))
        height = min(max(480, height), max(480, monitor.height - 80))
        x = monitor.left + (monitor.width - width) // 2
        y = monitor.top + (monitor.height - height) // 2
        return f"{width}x{height}+{x}+{y}"

    def switch_monitor(self, _event: object = None) -> str:
        """Move to the next active display and preserve fullscreen state."""

        try:
            monitors = enumerate_monitors()
        except (OSError, RuntimeError):
            self.root.bell()
            return "break"
        if len(monitors) < 2:
            self.root.bell()
            return "break"

        self.root.update_idletasks()
        current = self._monitor_for_window(monitors)
        current_index = monitors.index(current)
        target = monitors[(current_index + 1) % len(monitors)]

        if self.fullscreen:
            self.root.geometry(target.geometry)
            self.root.update_idletasks()
            self.root.lift()
            self.fullscreen_monitor = target
        else:
            self.root.geometry(
                self._centered_geometry(
                    target,
                    self.root.winfo_width(),
                    self.root.winfo_height(),
                )
            )
        self.layout_dirty = True
        self.root.after_idle(self._focus_canvas)
        return "break"

    def _focus_canvas(self) -> None:
        try:
            self.canvas.focus_set()
        except self.tk.TclError:
            pass

    def toggle_fullscreen(self, _event: object = None) -> str:
        self.set_fullscreen(not self.fullscreen)
        return "break"

    def leave_fullscreen(self, _event: object = None) -> str | None:
        if not self.fullscreen:
            return None
        self.set_fullscreen(False)
        return "break"

    def _layout(self) -> None:
        c = self.canvas
        width = max(1, c.winfo_width())
        height = max(1, c.winfo_height())
        if width < 100 or height < 100:
            self.layout_dirty = True
            return
        self.width, self.height = width, height
        margin = max(18, min(36, width // 32))

        vertical = 7
        horizontal = 5
        for index, item in enumerate(self.grid_lines):
            if index < vertical:
                x = (index + 1) * width / (vertical + 1)
                c.coords(item, x, 0, x, height)
            else:
                row = index - vertical
                y = (row + 1) * height / (horizontal + 1)
                c.coords(item, 0, y, width, y)

        for item, star in zip(self.star_items, self.stars):
            x, y = star.x * width, star.y * height
            c.coords(item, x - star.size, y - star.size, x + star.size, y + star.size)

        c.coords(self.hint, width - margin, height - margin)
        self.layout_dirty = False

    def _animate_aurora(self, elapsed: float) -> None:
        width, height = self.width, self.height
        for band, (glow, line) in enumerate(zip(self.aurora_glows, self.aurora_lines)):
            points: list[float] = []
            base = height * (0.44 + band * 0.07)
            amplitude = height * (0.07 - band * 0.009)
            for index in range(self.wave_points):
                ratio = index / (self.wave_points - 1)
                x = ratio * width
                wave = (
                    math.sin(ratio * math.tau * 1.22 + elapsed * (0.34 + band * 0.06) + band)
                    + 0.42 * math.sin(ratio * math.tau * 2.8 - elapsed * 0.21 + band * 1.7)
                )
                y = base + amplitude * wave
                points.extend((x, y))
            self.canvas.coords(glow, *points)
            self.canvas.coords(line, *points)

    @staticmethod
    def _node_activation(node: NeuralNode, elapsed: float) -> float:
        """Combine a left-to-right inference wave with local neuron spikes."""

        wave_phase = (elapsed * 0.14 - node.x * 0.92) % 1.0
        wave = math.exp(-((min(wave_phase, 1.0 - wave_phase) / 0.052) ** 2))
        local_phase = (elapsed * node.speed + node.phase / math.tau) % 1.0
        local = math.exp(-(local_phase * 18.0)) if local_phase < 0.20 else 0.0
        return clamp(max(wave, local * 0.86))

    def _animate_network(self, elapsed: float) -> None:
        c = self.canvas
        width, height = self.width, self.height
        positions = [
            (
                node.x * width + math.sin(elapsed * 0.13 + node.phase) * width * 0.0025,
                node.y * height + math.cos(elapsed * 0.17 + node.phase) * height * 0.0045,
            )
            for node in self.nodes
        ]
        self.node_positions = positions
        activations = [
            self._node_activation(node, elapsed) for node in self.nodes
        ]
        refresh_colors = self.frame_number % 3 == 0

        for edge, item in zip(self.edges, self.edge_items):
            source_x, source_y = positions[edge.source]
            target_x, target_y = positions[edge.target]
            c.coords(item, source_x, source_y, target_x, target_y)
            if refresh_colors:
                firing = max(activations[edge.source], activations[edge.target])
                shimmer = 0.5 + 0.5 * math.sin(elapsed * 0.37 + edge.phase)
                strength = 0.13 + firing * 0.62 + shimmer * 0.055
                c.itemconfigure(
                    item,
                    fill=mix(self.BG, self.accent, strength),
                    width=2 if firing > 0.64 else 1,
                )

        for index, node in enumerate(self.nodes):
            x, y = positions[index]
            activation = activations[index]
            radius = (2.0 + activation * 3.7) * node.size
            glow_radius = radius * (2.05 + activation * 1.15)
            c.coords(
                self.node_glows[index],
                x - glow_radius,
                y - glow_radius,
                x + glow_radius,
                y + glow_radius,
            )
            c.coords(
                self.node_items[index],
                x - radius,
                y - radius,
                x + radius,
                y + radius,
            )
            if refresh_colors:
                node_color = mix(self.accent, self.hot, activation * 0.72)
                c.itemconfigure(
                    self.node_glows[index],
                    fill=mix(self.BG, node_color, 0.12 + activation * 0.25),
                )
                c.itemconfigure(
                    self.node_items[index],
                    fill=mix(self.BG, node_color, 0.58 + activation * 0.30),
                    outline=mix(node_color, self.hot, 0.25 + activation * 0.60),
                )

        for index, pulse in enumerate(self.pulses):
            edge = self.edges[pulse.edge]
            source_x, source_y = positions[edge.source]
            target_x, target_y = positions[edge.target]
            progress = (elapsed * pulse.speed + pulse.phase) % 1.0
            eased = progress * progress * (3.0 - 2.0 * progress)
            x = source_x + (target_x - source_x) * eased
            y = source_y + (target_y - source_y) * eased
            flare = 0.72 + 0.28 * math.sin(progress * math.pi)
            outer = pulse.size * (2.8 + flare)
            inner = pulse.size * (0.72 + flare * 0.34)
            c.coords(
                self.pulse_glows[index],
                x - outer,
                y - outer,
                x + outer,
                y + outer,
            )
            c.coords(
                self.pulse_items[index],
                x - inner,
                y - inner,
                x + inner,
                y + inner,
            )
            if refresh_colors:
                c.itemconfigure(
                    self.pulse_glows[index],
                    fill=mix(self.BG, self.hot, 0.28 + flare * 0.12),
                )

    def _refresh_text(self, now: float) -> None:
        if now < self.next_text_refresh:
            return
        self.next_text_refresh = now + 0.25
        if self.frame_number % 8 == 0:
            for item, star in zip(self.star_items, self.stars):
                glow = 0.18 + 0.32 * (0.5 + 0.5 * math.sin((now - self.started) * star.speed + star.phase))
                self.canvas.itemconfigure(item, fill=mix(self.BG, self.hot, glow))

    def _tick(self) -> None:
        if not self.running:
            return
        frame_started = time.perf_counter()
        now = time.monotonic()
        self.last_frame = now
        self.frame_number += 1

        if self.layout_dirty:
            self._layout()
        if now >= self.next_awake_refresh:
            try:
                self.request.refresh()
                self.next_awake_refresh = now + 20.0
            except OSError as error:
                self._fatal_power_error(error)
                return
        if self.deadline is not None and now >= self.deadline:
            self.close()
            return

        elapsed = now - self.started
        self._animate_aurora(elapsed)
        self._animate_network(elapsed)
        self._refresh_text(now)

        spent_ms = (time.perf_counter() - frame_started) * 1000.0
        delay = max(1, round(self.frame_ms - spent_ms))
        self.after_id = self.root.after(delay, self._tick)

    def _fatal_power_error(self, error: OSError) -> None:
        self.failure_code = "POWER_REQUEST_FAILED"
        self.close()

    def close(self, _event: object = None) -> str:
        if not self.running:
            return "break"
        self.running = False
        try:
            self.root.after_cancel(self.after_id)
        except (AttributeError, self.tk.TclError):
            pass
        try:
            self.request.restore()
        except OSError:
            self.failure_code = self.failure_code or "RESTORATION_NOT_CONFIRMED"
            print("Warning: sleep-state restoration failed: POWER_REQUEST_CLEAR_FAILED", file=sys.stderr)
        try:
            self.root.destroy()
        except self.tk.TclError:
            pass
        return "break"


def run_visual(request: StayAwake, args: argparse.Namespace) -> None:
    try:
        import tkinter as tk
    except ImportError:
        raise RuntimeError("GUI_UNAVAILABLE_OR_FAILED") from None

    root = None
    try:
        enable_dpi_awareness()
        root = tk.Tk()
        if args.ui_smoke_test:
            root.attributes("-alpha", 0.0)
        _run_visual_app(root, request, args)
    except tk.TclError:
        raise RuntimeError("GUI_UNAVAILABLE_OR_FAILED") from None
    finally:
        if root is not None:
            try:
                root.destroy()
            except tk.TclError:
                pass


def _run_visual_app(root: object, request: StayAwake, args: argparse.Namespace) -> None:
    app = None
    callback_error = None

    def callback_failed(_kind: object, _value: object, _traceback: object) -> None:
        nonlocal callback_error
        callback_error = "GUI_CALLBACK_FAILED"
        if app is None:
            root.destroy()
        else:
            app.failure_code = app.failure_code or callback_error
            app.close()

    root.report_callback_exception = callback_failed
    app = AwakeApp(
        root,
        request,
        quality=args.quality,
        theme=args.theme,
        fps=args.fps,
        fullscreen=args.fullscreen,
        minutes=args.minutes,
        smoke_test=args.ui_smoke_test,
    )

    try:
        if callback_error is not None:
            raise RuntimeError(callback_error)
        _run_visual_loop(root, app, args)
    finally:
        app.close()
    if app.failure_code is not None:
        raise RuntimeError(app.failure_code)


def _run_visual_loop(root: object, app: AwakeApp, args: argparse.Namespace) -> None:
    if args.ui_smoke_test:
        root.attributes("-alpha", 0.0)
        root.update_idletasks()
        start = time.perf_counter()
        for frame in range(60):
            app._animate_aurora(frame / args.fps)
            app.frame_number = frame
            app._animate_network(frame / args.fps)
        root.update_idletasks()
        frame_ms = (time.perf_counter() - start) / 60 * 1000
        item_count = len(app.canvas.find_all())
        app.set_fullscreen(True)
        _require(app.fullscreen, "UI_SMOKE_FAILED")
        _require(bool(root.overrideredirect()), "UI_SMOKE_FAILED")
        _require(bool(root.bind_all("<Key-n>")), "UI_SMOKE_FAILED")
        monitors = enumerate_monitors()
        _require(bool(monitors) and all(item.width > 0 and item.height > 0 for item in monitors), "UI_SMOKE_FAILED")
        if len(monitors) > 1:
            first_monitor = app.fullscreen_monitor
            _require(app.switch_monitor() == "break", "UI_SMOKE_FAILED")
            root.update_idletasks()
            _require(app.fullscreen_monitor is not None, "UI_SMOKE_FAILED")
            _require(app.fullscreen_monitor != first_monitor, "UI_SMOKE_FAILED")
            _require(root.winfo_rootx() == app.fullscreen_monitor.left, "UI_SMOKE_FAILED")
            _require(root.winfo_rooty() == app.fullscreen_monitor.top, "UI_SMOKE_FAILED")
        _require(app.leave_fullscreen() == "break", "UI_SMOKE_FAILED")
        _require(not app.fullscreen, "UI_SMOKE_FAILED")
        _require(not bool(root.overrideredirect()), "UI_SMOKE_FAILED")
        _require(app.leave_fullscreen() is None, "UI_SMOKE_FAILED")
        app.close()
        _require(app.failure_code is None, app.failure_code or "UI_SMOKE_FAILED")
        print(
            f"UI smoke test passed: {item_count} persistent canvas items, "
            f"{frame_ms:.2f} ms per high-motion frame."
        )
        return
    root.mainloop()
    if app.failure_code is not None:
        raise RuntimeError(app.failure_code)


def run_console(request: StayAwake, minutes: float) -> None:
    started = time.monotonic()
    deadline = started + minutes * 60 if minutes else None
    print(f"{APP_NAME} {VERSION} — system/display keep-awake request active")
    print("Press Ctrl+C or close this window to stop.")
    while deadline is None or time.monotonic() < deadline:
        request.refresh()
        time.sleep(
            min(20.0, max(0.05, deadline - time.monotonic()))
            if deadline is not None
            else 20.0
        )


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError(code)


def self_test() -> None:
    _require(clamp(-1) == 0, "SELF_TEST_FAILED")
    _require(clamp(2) == 1, "SELF_TEST_FAILED")
    _require(mix("#000000", "#ffffff", 0.5) == "#808080", "SELF_TEST_FAILED")
    _require(duration_text(3661.9) == "01:01:01", "SELF_TEST_FAILED")
    _require(nonnegative_minutes("2.5") == 2.5, "SELF_TEST_FAILED")
    _require(set(QUALITY) == {"low", "balanced", "high"}, "SELF_TEST_FAILED")
    monitor = MonitorBounds(-1920, 0, 0, 1080)
    _require(monitor.width == 1920 and monitor.height == 1080, "SELF_TEST_FAILED")
    _require(monitor.geometry == "1920x1080+-1920+0", "SELF_TEST_FAILED")
    _require(monitor.contains(-100, 500), "SELF_TEST_FAILED")
    _require(not monitor.contains(100, 500), "SELF_TEST_FAILED")
    _require(bool(enumerate_monitors()), "SELF_TEST_FAILED")
    with StayAwake() as request:
        _require(request.active, "SELF_TEST_FAILED")
        request.refresh()
    _require(not request.active, "RESTORATION_NOT_CONFIRMED")
    print("Self-test passed: helper checks and native request acquire/clear calls succeeded.")


def _runtime_error_code(error: Exception) -> str:
    code = str(error)
    return code if code in {
        "REQUEST_THREAD_MISMATCH", "POWER_REQUEST_FAILED", "POWER_REQUEST_CLEAR_FAILED",
        "RESTORATION_NOT_CONFIRMED", "GUI_UNAVAILABLE_OR_FAILED", "GUI_CALLBACK_FAILED",
        "SELF_TEST_FAILED", "UI_SMOKE_FAILED",
    } else "RUNTIME_FAILED"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError("ARGUMENTS_INVALID")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="keep_awake.py",
        description=(
            "Keep a Windows PC and its display awake with a lightweight "
            "fullscreen animated status field."
        )
    )
    parser.add_argument(
        "--quality",
        choices=("auto", "low", "balanced", "high"),
        default="auto",
        help="visual density (default: auto)",
    )
    parser.add_argument(
        "--fullscreen", "-f", action="store_true",
        help="start in fullscreen; F11 toggles and Escape exits fullscreen",
    )
    parser.add_argument(
        "--theme",
        choices=tuple(THEMES),
        default="cyan",
        help="visual color theme (default: cyan)",
    )
    parser.add_argument(
        "--fps", type=int, choices=range(10, 61), default=30, metavar="10-60",
        help="animation frame rate (default: 30)",
    )
    parser.add_argument(
        "--minutes", "-m", type=nonnegative_minutes, default=0.0, metavar="NUMBER",
        help="stop after this many minutes; 0 means until exit",
    )
    parser.add_argument(
        "--no-visual", action="store_true",
        help="run a quiet terminal keep-awake loop",
    )
    # Accepted for compatibility with the previous script.
    parser.add_argument("--minimized", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--pattern", choices=("auto", "uniform", "random"), help=argparse.SUPPRESS)
    parser.add_argument("--keep-display-on", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--self-test", action="store_true", help="test the Windows power request, then exit")
    parser.add_argument("--ui-smoke-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except ValueError:
        print("Error: ARGUMENTS_INVALID", file=sys.stderr)
        return 2
    if sys.platform != "win32":
        print("Error: WINDOWS_REQUIRED", file=sys.stderr)
        return 1
    if args.self_test:
        try:
            self_test()
        except KeyboardInterrupt:
            print("Error: SELF_TEST_INTERRUPTED", file=sys.stderr)
            return 1
        except Exception as error:
            print(f"Self-test failed: {_runtime_error_code(error)}", file=sys.stderr)
            return 1
        return 0

    request = None
    try:
        with StayAwake() as request:
            if args.no_visual:
                run_console(request, args.minutes)
            else:
                run_visual(request, args)
    except KeyboardInterrupt:
        print("\nStop requested.")
    except Exception as error:
        print(f"Error: {_runtime_error_code(error)}", file=sys.stderr)
        return 1
    finally:
        print("Cleanup attempted; check warnings before assuming sleep behavior was restored.")
    if request is not None and request.active:
        print("Error: RESTORATION_NOT_CONFIRMED", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
