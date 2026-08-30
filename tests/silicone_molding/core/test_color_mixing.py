"""Calibrated optical-density mixing for silicone colorants."""

import pytest

from silicone_molding.core import CalibratedColorant, simulate_silicone_color

WHITE = (1.0, 1.0, 1.0)


def test_no_colorant_preserves_the_base_color() -> None:
    base = (1.0, 0.9, 0.7)

    result = simulate_silicone_color(base, 100.0, [])

    assert result == pytest.approx(base)


def test_reference_dose_reproduces_its_calibration_color() -> None:
    calibration = (0.8, 0.2, 0.1)
    colorant = CalibratedColorant(calibration, 2.0, 2.0)

    result = simulate_silicone_color(WHITE, 100.0, [colorant])

    assert result == pytest.approx(calibration)


def test_doubling_base_volume_halves_the_optical_density() -> None:
    colorant = CalibratedColorant((0.25, 0.64, 0.81), 1.0, 1.0)

    result = simulate_silicone_color(WHITE, 200.0, [colorant])

    assert result == pytest.approx((0.5, 0.8, 0.9))


def test_multiple_colorants_are_independent_of_row_order() -> None:
    red = CalibratedColorant((0.9, 0.3, 0.3), 1.0, 0.75)
    blue = CalibratedColorant((0.3, 0.4, 0.9), 2.0, 1.25)

    forward = simulate_silicone_color(WHITE, 80.0, [red, blue])
    reverse = simulate_silicone_color(WHITE, 80.0, [blue, red])

    assert forward == pytest.approx(reverse)


def test_disabled_and_zero_drop_rows_do_not_contribute() -> None:
    ignored = [
        CalibratedColorant((0.1, 0.2, 0.3), 1.0, 5.0, enabled=False),
        CalibratedColorant((0.2, 0.3, 0.4), 1.0, 0.0),
    ]

    result = simulate_silicone_color(WHITE, 100.0, ignored)

    assert result == pytest.approx(WHITE)


def test_calibration_cannot_make_a_channel_brighter_than_the_base() -> None:
    base = (0.8, 0.7, 0.6)
    colorant = CalibratedColorant((0.9, 0.5, 0.3), 1.0, 1.0)

    result = simulate_silicone_color(base, 100.0, [colorant])

    assert result == pytest.approx((0.8, 0.5, 0.3))


@pytest.mark.parametrize("volume", [0.0, -1.0])
def test_non_positive_base_volume_is_rejected(volume: float) -> None:
    with pytest.raises(ValueError, match="volume"):
        simulate_silicone_color(WHITE, volume, [])


def test_non_positive_reference_drops_are_rejected_when_used() -> None:
    colorant = CalibratedColorant((0.5, 0.5, 0.5), 0.0, 1.0)

    with pytest.raises(ValueError, match="Reference"):
        simulate_silicone_color(WHITE, 100.0, [colorant])
