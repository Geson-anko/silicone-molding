"""Compatibility facade for the add-on's panels and UI lists."""

# pyright: reportPrivateUsage=false

from ._color_panel import (
    SILMOLD_PT_color_simulator as SILMOLD_PT_color_simulator,
    SILMOLD_UL_color_profiles as SILMOLD_UL_color_profiles,
    SILMOLD_UL_colorants as SILMOLD_UL_colorants,
    draw_color_simulator as draw_color_simulator,
)
from ._mixture_panel import (
    _MIXTURE_COLUMN_WEIGHTS as _MIXTURE_COLUMN_WEIGHTS,
    SILMOLD_PT_mixture_calculator as SILMOLD_PT_mixture_calculator,
    SILMOLD_UL_mixture_parts as SILMOLD_UL_mixture_parts,
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
    SILMOLD_PT_coloring as SILMOLD_PT_coloring,
    SILMOLD_PT_main as SILMOLD_PT_main,
    SILMOLD_PT_measurement as SILMOLD_PT_measurement,
    SILMOLD_PT_processing as SILMOLD_PT_processing,
)
