"""Compatibility facade for the add-on's panels and UI lists."""

# pyright: reportPrivateUsage=false

from ._color_panel import (
    SILCAST_PT_color_simulator as SILCAST_PT_color_simulator,
    SILCAST_UL_color_profiles as SILCAST_UL_color_profiles,
    SILCAST_UL_colorants as SILCAST_UL_colorants,
    draw_color_simulator as draw_color_simulator,
)
from ._mixture_panel import (
    _MIXTURE_COLUMN_WEIGHTS as _MIXTURE_COLUMN_WEIGHTS,
    SILCAST_PT_mixture_calculator as SILCAST_PT_mixture_calculator,
    SILCAST_UL_mixture_parts as SILCAST_UL_mixture_parts,
    _draw_mixture_header as _draw_mixture_header,
    _draw_mixture_output_cell as _draw_mixture_output_cell,
    _draw_mixture_part as _draw_mixture_part,
    _draw_mixture_summary as _draw_mixture_summary,
    _filter_mixture_parts_by_name as _filter_mixture_parts_by_name,
    _included_mixture_volume as _included_mixture_volume,
    _mixture_breakdown as _mixture_breakdown,
    _mixture_table_cells as _mixture_table_cells,
    _MixturePartValues as _MixturePartValues,
    _MixtureSettings as _MixtureSettings,
    draw_mixture_calculator as draw_mixture_calculator,
)
from ._sidebar_panels import (
    _NOT_MEASURED as _NOT_MEASURED,
    _VOLUME_LABEL as _VOLUME_LABEL,
    SILCAST_PT_coloring as SILCAST_PT_coloring,
    SILCAST_PT_main as SILCAST_PT_main,
    SILCAST_PT_measurement as SILCAST_PT_measurement,
    SILCAST_PT_processing as SILCAST_PT_processing,
)
