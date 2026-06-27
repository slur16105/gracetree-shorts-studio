"""Story 2.5: Typed subtitle layout config for 1080×1920 Korean prayer videos."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubtitleConfig:
    # Resolution
    play_res_x: int = 1080
    play_res_y: int = 1920

    # Font
    # Black Han Sans (검은고딕): heavy single-weight display font matching the
    # CapCut Shorts caption look. Matched by its ASCII family name via libass
    # fontsdir. NanumGothic stays bundled as a per-glyph fallback for any
    # syllable this display font does not cover.
    font_name: str = "Black Han Sans"
    # Sizes doubled from the original 72/52/60 for a punchy Shorts look. libass
    # wraps within margin_h so the larger text does not clip horizontally.
    font_size_title: int = 144
    font_size_scripture: int = 104
    font_size_prayer: int = 120

    # ASS colors: &HAABBGGRR (alpha, blue, green, red)
    color_title: str = "&H00FFFFFF"       # white
    color_scripture: str = "&H00FFFFFF"   # white
    color_prayer: str = "&H00FFFFFF"      # white
    color_outline: str = "&H00000000"     # black
    color_shadow: str = "&H80000000"      # 50% transparent black

    # Border/shadow
    outline_thickness: int = 3
    shadow_depth: int = 2

    # Fade
    fade_in_ms: int = 300
    fade_out_ms: int = 200

    # Safe area margins (pixels from edge)
    margin_h: int = 108       # 10% of 1080
    margin_v_top: int = 192   # 10% of 1920 top

    # Vertical gap between title and scripture text
    title_scripture_gap: int = 20

    # The intro background has a black band across the top ~30% of the 1080×1920
    # frame. Title and scripture are anchored to this point (\pos + \an5) so they
    # sit centred in that band regardless of line count. Tune if the band moves.
    title_band_center_v: int = 288  # ≈ centre of the top 30% (0–576px) band

    # 아멘 hold and fade
    amen_hold_seconds: float = 2.0
    amen_fade_out_ms: int = 500

    # Max lines per prayer block before safe-area error
    max_prayer_lines: int = 8


DEFAULT_SUBTITLE_CONFIG = SubtitleConfig()
