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
    calibration_drops_per_ml: float
    drops: float
    enabled: bool = True
    is_opacifier: bool = False


@dataclass(frozen=True, slots=True)
class SimulatedSiliconeAppearance:
    """Calculated color and optical appearance of one silicone mixture."""

    color: RGB
    transparency: float
    cloudiness: float


def _clamp_unit(value: float) -> float:
    """Clamp one scalar to the inclusive zero-to-one range."""
    return min(max(value, 0.0), 1.0)


def _concentration_factor(
    colorant: CalibratedColorant,
    base_volume_ml: float,
) -> float:
    """Return actual concentration relative to one colorant's calibration."""
    if colorant.calibration_drops_per_ml <= 0.0:
        raise ValueError("Calibration drops per mL must be greater than zero")
    return colorant.drops / (base_volume_ml * colorant.calibration_drops_per_ml)


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

    Each calibration color is the observed color at its dye-specific
    calibration drops per mL in the currently selected base. Optical-
    density contributions are scaled by the actual concentration, then
    added so the result is independent of row order.
    """
    if base_volume_ml <= 0.0:
        raise ValueError("Base volume must be greater than zero")

    base_absorbance = _absorbance(base_color)
    total_absorbance = list(base_absorbance)

    for colorant in colorants:
        if not colorant.enabled or colorant.drops <= 0.0:
            continue
        calibration_absorbance = _absorbance(colorant.calibration_color)
        concentration_factor = _concentration_factor(colorant, base_volume_ml)
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


def simulate_silicone_appearance(
    base_color: RGB,
    base_volume_ml: float,
    base_transparency: float,
    base_cloudiness: float,
    colorants: Iterable[CalibratedColorant],
) -> SimulatedSiliconeAppearance:
    """Return color, transparency, and cloudiness for a calibrated mixture.

    Opacifier rows reach fully opaque and milky at their calibration
    concentration. Multiple opacifiers add their relative
    concentrations, capped at the calibrated endpoint.
    """
    colorant_values = tuple(colorants)
    color = simulate_silicone_color(base_color, base_volume_ml, colorant_values)
    opacifier_factor = sum(
        _concentration_factor(colorant, base_volume_ml)
        for colorant in colorant_values
        if colorant.enabled and colorant.is_opacifier and colorant.drops > 0.0
    )
    opacity_factor = _clamp_unit(opacifier_factor)
    transparency = _clamp_unit(base_transparency) * (1.0 - opacity_factor)
    base_cloudiness = _clamp_unit(base_cloudiness)
    cloudiness = base_cloudiness + (1.0 - base_cloudiness) * opacity_factor
    return SimulatedSiliconeAppearance(color, transparency, cloudiness)


def linear_rgb_to_srgb8(color: RGB) -> tuple[int, int, int]:
    """Convert scene-linear RGB to conventional 8-bit sRGB values."""

    def convert(channel: float) -> int:
        linear = _clamp_unit(channel)
        srgb = (
            12.92 * linear
            if linear <= 0.0031308
            else 1.055 * linear ** (1.0 / 2.4) - 0.055
        )
        return int(srgb * 255.0 + 0.5)

    return (convert(color[0]), convert(color[1]), convert(color[2]))


def format_hex_color(color: RGB) -> str:
    """Format scene-linear RGB as a copy-ready sRGB hex color code."""
    red, green, blue = linear_rgb_to_srgb8(color)
    return f"#{red:02X}{green:02X}{blue:02X}"


def format_linear_rgb(color: RGB) -> str:
    """Format scene-linear RGB as a stable copy-ready triplet."""
    return ", ".join(f"{_clamp_unit(channel):.4f}" for channel in color)
