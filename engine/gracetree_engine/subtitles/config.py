"""Story 2.5: Typed subtitle layout config for 1080×1920 Korean prayer videos."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubtitleConfig:
    # Resolution
    play_res_x: int = 1080
    play_res_y: int = 1920

    # Font
    font_name: str = "나눔고딕"
    font_size_title: int = 72
    font_size_scripture: int = 52
    font_size_prayer: int = 60

    # ASS colors: &HAABBGGRR (alpha, blue, green, red)
    color_title: str = "&H00FFFFFF"       # white
    color_scripture: str = "&H00AAAAAA"   # light gray
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

    # 아멘 hold and fade
    amen_hold_seconds: float = 2.0
    amen_fade_out_ms: int = 500

    # Max lines per prayer block before safe-area error
    max_prayer_lines: int = 8


DEFAULT_SUBTITLE_CONFIG = SubtitleConfig()
