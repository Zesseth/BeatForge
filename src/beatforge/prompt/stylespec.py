"""Schema for StyleSpec — the structured representation of a drum prompt.

The schema is deliberately small in v1; future milestones may add fields,
but new fields MUST be optional with a default so old StyleSpecs remain
parseable.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Genre = Literal["rock", "pop", "punk", "metal", "funk"]
Hats = Literal["8th", "16th", "shuffle", "swing"]
Backbeat = Literal["2_and_4", "2", "4"]
Density = Literal["less", "default", "more"]
Fills = Literal["none", "fewer", "default", "more", "before_chorus"]
Feel = Literal["tight", "default", "loose"]


class StyleSpec(BaseModel):
    """Structured intent extracted from a natural-language drum prompt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    genre: Genre | None = None
    bpm: int | None = Field(default=None, ge=20, le=400)
    hats: Hats | None = None
    backbeat: Backbeat | None = None
    kick_density: Density = "default"
    fills: Fills = "default"
    ghost_notes: bool = False
    feel: Feel = "default"
