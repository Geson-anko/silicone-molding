"""Approximate subtractive mixing for calibrated silicone colorants."""

from collections.abc import Iterable
from colorsys import hls_to_rgb, rgb_to_hls
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


def _is_white(color: RGB) -> bool:
    """Return whether a saturated-HSL calibration is the white endpoint."""
    return all(_clamp_unit(channel) == 1.0 for channel in color)


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
        if not colorant.enabled or _is_white(colorant.calibration_color):
            continue
        if colorant.drops <= 0.0:
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

    All dyes reduce transmission at their calibration concentration. A
    white calibration is detected automatically. White additionally
    lightens the subtractive dye result and increases cloudiness; black
    and every non-white color use subtractive darkening.
    """
    colorant_values = tuple(colorants)
    color = simulate_silicone_color(base_color, base_volume_ml, colorant_values)
    active_colorants = tuple(
        (colorant, _concentration_factor(colorant, base_volume_ml))
        for colorant in colorant_values
        if colorant.enabled and colorant.drops > 0.0
    )
    opacity_factor = _clamp_unit(
        sum(concentration for _colorant, concentration in active_colorants)
    )
    transparency = _clamp_unit(base_transparency) * (1.0 - opacity_factor)

    white_colorants = tuple(
        (colorant, concentration)
        for colorant, concentration in active_colorants
        if _is_white(colorant.calibration_color)
    )
    white_factor = sum(concentration for _colorant, concentration in white_colorants)
    white_coverage = _clamp_unit(white_factor)
    if white_coverage > 0.0:
        color = (
            color[0] + (1.0 - color[0]) * white_coverage,
            color[1] + (1.0 - color[1]) * white_coverage,
            color[2] + (1.0 - color[2]) * white_coverage,
        )

    base_cloudiness = _clamp_unit(base_cloudiness)
    cloudiness = base_cloudiness + (1.0 - base_cloudiness) * white_coverage
    return SimulatedSiliconeAppearance(color, transparency, cloudiness)


def _linear_channel_to_srgb(channel: float) -> float:
    """Convert one scene-linear channel to an sRGB channel."""
    linear = _clamp_unit(channel)
    return (
        12.92 * linear if linear <= 0.0031308 else 1.055 * linear ** (1.0 / 2.4) - 0.055
    )


def _srgb_channel_to_linear(channel: float) -> float:
    """Convert one sRGB channel to a scene-linear channel."""
    srgb = _clamp_unit(channel)
    return srgb / 12.92 if srgb <= 0.04045 else ((srgb + 0.055) / 1.055) ** 2.4


def saturated_hsl_to_linear_rgb(hue_degrees: float, lightness: float) -> RGB:
    """Create scene-linear RGB from HSL with saturation fixed at 100%."""
    hue = (hue_degrees % 360.0) / 360.0
    srgb = hls_to_rgb(hue, _clamp_unit(lightness), 1.0)
    return (
        _srgb_channel_to_linear(srgb[0]),
        _srgb_channel_to_linear(srgb[1]),
        _srgb_channel_to_linear(srgb[2]),
    )


def linear_rgb_to_hsl(color: RGB) -> tuple[float, float, float]:
    """Return conventional sRGB HSL as degrees, saturation, and lightness."""
    srgb = tuple(_linear_channel_to_srgb(channel) for channel in color)
    hue, lightness, saturation = rgb_to_hls(*srgb)
    return (hue * 360.0, saturation, lightness)


def linear_rgb_to_srgb8(color: RGB) -> tuple[int, int, int]:
    """Convert scene-linear RGB to conventional 8-bit sRGB values."""

    def convert(channel: float) -> int:
        srgb = _linear_channel_to_srgb(channel)
        return int(srgb * 255.0 + 0.5)

    return (convert(color[0]), convert(color[1]), convert(color[2]))


def format_hex_color(color: RGB) -> str:
    """Format scene-linear RGB as a copy-ready sRGB hex color code."""
    red, green, blue = linear_rgb_to_srgb8(color)
    return f"#{red:02X}{green:02X}{blue:02X}"


def format_linear_rgb(color: RGB) -> str:
    """Format scene-linear RGB as a stable copy-ready triplet."""
    return ", ".join(f"{_clamp_unit(channel):.4f}" for channel in color)
