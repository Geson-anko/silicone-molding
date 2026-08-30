"""Approximate subtractive mixing for calibrated silicone colorants."""

from collections.abc import Iterable
from dataclasses import dataclass
from math import exp, log

RGB = tuple[float, float, float]

_MIN_CHANNEL = 1e-6


@dataclass(frozen=True, slots=True)
class CalibratedColorant:
    """One colorant dose calibrated against the current silicone base."""

    calibration_color: RGB
    reference_drops_per_100_ml: float
    drops: float
    enabled: bool = True


def _absorbance(color: RGB) -> RGB:
    """Convert scene-linear transmittance-like RGB to optical density."""
    return (
        -log(min(max(color[0], _MIN_CHANNEL), 1.0)),
        -log(min(max(color[1], _MIN_CHANNEL), 1.0)),
        -log(min(max(color[2], _MIN_CHANNEL), 1.0)),
    )


def simulate_silicone_color(
    base_color: RGB,
    base_volume_ml: float,
    colorants: Iterable[CalibratedColorant],
) -> RGB:
    """Return a scene-linear RGB estimate for a calibrated colorant mixture.

    Each calibration color is the observed color at its reference dose
    in the currently selected base. Optical-density contributions are
    scaled by the actual drops per 100 mL, then added so the result is
    independent of row order.
    """
    if base_volume_ml <= 0.0:
        raise ValueError("Base volume must be greater than zero")

    base_absorbance = _absorbance(base_color)
    total_absorbance = list(base_absorbance)

    for colorant in colorants:
        if not colorant.enabled or colorant.drops <= 0.0:
            continue
        if colorant.reference_drops_per_100_ml <= 0.0:
            raise ValueError("Reference drops must be greater than zero")

        calibration_absorbance = _absorbance(colorant.calibration_color)
        concentration_factor = (
            colorant.drops * 100.0 / base_volume_ml
        ) / colorant.reference_drops_per_100_ml
        for channel in range(3):
            contribution = max(
                calibration_absorbance[channel] - base_absorbance[channel],
                0.0,
            )
            total_absorbance[channel] += contribution * concentration_factor

    return (
        exp(-total_absorbance[0]),
        exp(-total_absorbance[1]),
        exp(-total_absorbance[2]),
    )
