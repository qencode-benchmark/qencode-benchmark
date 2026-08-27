"""Named, versioned gate-noise models.

The suite's central discipline is that a configuration is a *name*, not a set of knobs a
submitter chose. A noise model is a configuration like any other: "depolarizing noise"
is not a specification, because it does not say which channels act on which gates at what
rates. Everything here is pinned so that two people quoting the same name ran the same
thing, and so a noise model can be recorded in an entry and rebuilt from the record.

Rates are per-gate error probabilities. The defaults are chosen to bracket current
superconducting hardware rather than to flatter it: two-qubit error around 5e-3 is roughly
where good devices sit today, 1e-3 is optimistic, 1e-2 is ordinary.

Gate noise differs from shot noise in a way that governs how results must be read. Shot
noise is zero mean -- more shots shrink it and the expectation is unbiased. Gate noise is
a *bias*: every channel here is dissipative, driving the state toward the maximally mixed
state, whose energy is the mean of the spectrum and therefore higher than the ground
state. Averaging more samples does not remove it.
"""
from __future__ import annotations

from typing import Callable, Dict, List

import pennylane as qml

SCHEMA_VERSION = "1"


def _depolarizing(p1: float, p2: float):
    """Depolarizing channel after every gate. The standard first approximation and the
    only one whose effect on an expectation value is analytically simple."""
    def after_1q(wire):
        if p1 > 0:
            qml.DepolarizingChannel(p1, wires=wire)

    def after_2q(wires):
        if p2 > 0:
            for w in wires:
                qml.DepolarizingChannel(p2, wires=w)
    return after_1q, after_2q


def _device_sc(p1: float, p2: float, gamma_amp: float, gamma_phase: float):
    """Depolarizing plus amplitude and phase damping, which is closer to what a
    superconducting device actually does: T1 relaxation toward |0> and T2 dephasing are
    not symmetric, and a purely depolarizing model misses that asymmetry."""
    def after_1q(wire):
        if p1 > 0:
            qml.DepolarizingChannel(p1, wires=wire)
        if gamma_amp > 0:
            qml.AmplitudeDamping(gamma_amp, wires=wire)
        if gamma_phase > 0:
            qml.PhaseDamping(gamma_phase, wires=wire)

    def after_2q(wires):
        for w in wires:
            if p2 > 0:
                qml.DepolarizingChannel(p2, wires=w)
            if gamma_amp > 0:
                qml.AmplitudeDamping(gamma_amp, wires=w)
            if gamma_phase > 0:
                qml.PhaseDamping(gamma_phase, wires=w)
    return after_1q, after_2q


# Every model is a complete specification. `params` is what gets recorded.
NOISE_MODELS: Dict[str, dict] = {
    "ideal/v1": {
        "description": "No noise. The control, and what every published entry used.",
        "device": "default.qubit",
        "params": {},
        "factory": lambda: ((lambda wire: None), (lambda wires: None)),
    },
    "depolarizing-opt/v1": {
        "description": "Depolarizing after each gate at optimistic rates "
                       "(1q 1e-4, 2q 1e-3). Better than current hardware.",
        "device": "default.mixed",
        "params": {"p_1q": 1e-4, "p_2q": 1e-3, "channels": ["depolarizing"]},
        "factory": lambda: _depolarizing(1e-4, 1e-3),
    },
    "depolarizing-current/v1": {
        "description": "Depolarizing after each gate at rates near good current "
                       "superconducting hardware (1q 5e-4, 2q 5e-3).",
        "device": "default.mixed",
        "params": {"p_1q": 5e-4, "p_2q": 5e-3, "channels": ["depolarizing"]},
        "factory": lambda: _depolarizing(5e-4, 5e-3),
    },
    "depolarizing-pessimistic/v1": {
        "description": "Depolarizing after each gate at ordinary-device rates "
                       "(1q 1e-3, 2q 1e-2).",
        "device": "default.mixed",
        "params": {"p_1q": 1e-3, "p_2q": 1e-2, "channels": ["depolarizing"]},
        "factory": lambda: _depolarizing(1e-3, 1e-2),
    },
    "device-sc/v1": {
        "description": "Depolarizing plus amplitude and phase damping at rates near "
                       "current superconducting hardware. Asymmetric, unlike pure "
                       "depolarizing: amplitude damping drives toward |0>.",
        "device": "default.mixed",
        "params": {"p_1q": 5e-4, "p_2q": 5e-3, "gamma_amplitude": 1e-3,
                   "gamma_phase": 1e-3,
                   "channels": ["depolarizing", "amplitude_damping", "phase_damping"]},
        "factory": lambda: _device_sc(5e-4, 5e-3, 1e-3, 1e-3),
    },
}


def get(name: str):
    """Return (device_name, after_1q, after_2q, spec) for a named model."""
    if name not in NOISE_MODELS:
        raise KeyError("unknown noise model %r; known: %s"
                       % (name, ", ".join(sorted(NOISE_MODELS))))
    m = NOISE_MODELS[name]
    a1, a2 = m["factory"]()
    spec = {"noise_model": name, "schema_version": SCHEMA_VERSION,
            "device": m["device"], "params": dict(m["params"])}
    return m["device"], a1, a2, spec


def scaled(name: str, scale: float):
    """A named model with every rate multiplied by `scale`, for sweeps.

    Returned spec records both the base name and the scale, so a swept point is still a
    complete specification rather than an anonymous set of numbers.
    """
    m = NOISE_MODELS[name]
    p = m["params"]
    if not p:
        return get(name)
    p1 = p.get("p_1q", 0.0) * scale
    p2 = p.get("p_2q", 0.0) * scale
    if "amplitude_damping" in p.get("channels", []):
        a1, a2 = _device_sc(p1, p2, p.get("gamma_amplitude", 0.0) * scale,
                            p.get("gamma_phase", 0.0) * scale)
    else:
        a1, a2 = _depolarizing(p1, p2)
    spec = {"noise_model": name, "schema_version": SCHEMA_VERSION,
            "device": m["device"], "scale": scale,
            "params": {k: (v * scale if isinstance(v, (int, float)) else v)
                       for k, v in p.items()}}
    return m["device"], a1, a2, spec


def names() -> List[str]:
    return sorted(NOISE_MODELS)
