"""PlanOptions — the PCC 5.x "accorgimenti" selector.

One object the user toggles in the UI. It is passed to ``training_planner.
generate_plan`` and ONLY switches on layers that enrich the single plan —
it never spawns a parallel planner. With ``mode="normal"`` (or every flag
False) the plan is byte-for-byte the same as 4.4.0 (contract: non-
regression test).

Layers and what each enriches (see docs/PCC_5x_ROADMAP.md and
docs/ricerca_worldtour_pro_2025-2026.md for sources):
  enable_nutrition     -> per-session fueling note (Impey 2018 / IOC)
  enable_integrators   -> supplement note per block (IOC/ISSN)
  enable_heat          -> heat/acclimation 14gg + pre-cooling (meta-2024)
  enable_strength      -> periodised strength 2x/sett + VBT, real sessions (meta-2025)
  enable_mobility      -> hip-flexor / core / aero, real sessions (Roadman 2025)
  enable_dfa_durability-> DFA a1 durability flag (HRV-in-sport 2025)
  enable_altitude     -> altitude block pre-event (Giro top-5 / TdF2025)
  enable_auto_replan   -> continuous re-planning (continuous_policy, already in app)
  enable_notifications -> notification layer (notifications.py; view, not plan)

Each layer is a pure function in training_planner that takes the plan and
returns the enriched plan; turned off it is a no-op.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PlanOptions:
    # "normal" forces every flag off -> classic planner behaviour.
    mode: str = "normal"
    enable_nutrition: bool = False
    enable_integrators: bool = False
    enable_heat: bool = False
    enable_strength: bool = False
    enable_mobility: bool = False
    enable_dfa_durability: bool = False
    enable_altitude: bool = False
    enable_auto_replan: bool = False
    enable_notifications: bool = False

    def __post_init__(self):
        # B3 fix: if the caller passed any flag explicitly True, honour it even
        # when mode was left at the "normal" default. Only force everything off
        # when mode is literally "normal" AND no flag was turned on.
        any_explicit = any(
            getattr(self, f"enable_{n}")
            for n in ("nutrition", "integrators", "heat", "strength",
                      "mobility", "dfa_durability", "altitude", "auto_replan",
                      "notifications")
        )
        if self.mode == "normal" and not any_explicit:
            # Hard rule: normal mode = no accorgimenti.
            self.enable_nutrition = False
            self.enable_integrators = False
            self.enable_heat = False
            self.enable_strength = False
            self.enable_mobility = False
            self.enable_dfa_durability = False
            self.enable_altitude = False
            self.enable_auto_replan = False
            self.enable_notifications = False
        elif self.mode == "normal" and any_explicit:
            # Caller set flags but forgot mode -> promote to accorgimenti.
            self.mode = "accorgimenti"

    @property
    def is_normal(self) -> bool:
        return self.mode == "normal"

    @property
    def any_enabled(self) -> bool:
        return any(
            getattr(self, f"enable_{n}")
            for n in ("nutrition", "integrators", "heat", "strength",
                      "mobility", "dfa_durability", "altitude", "auto_replan",
                      "notifications")
        )

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "enable_nutrition": self.enable_nutrition,
            "enable_integrators": self.enable_integrators,
            "enable_heat": self.enable_heat,
            "enable_strength": self.enable_strength,
            "enable_mobility": self.enable_mobility,
            "enable_dfa_durability": self.enable_dfa_durability,
            "enable_altitude": self.enable_altitude,
            "enable_auto_replan": self.enable_auto_replan,
            "enable_notifications": self.enable_notifications,
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> "PlanOptions":
        if not d:
            return cls()
        known = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in (d or {}).items() if k in known}
        # B3 fix: if any accorgimento flag is explicitly True but mode was not
        # set to "accorgimenti", treat it as enabled. Otherwise a caller that
        # sends {"enable_heat": true} without "mode" would have every flag
        # silently zeroed by __post_init__ (mode defaults to "normal").
        flags_on = [k for k in (
            "enable_nutrition", "enable_integrators", "enable_heat",
            "enable_strength", "enable_mobility", "enable_dfa_durability",
            "enable_altitude", "enable_auto_replan", "enable_notifications",
        ) if kwargs.get(k) is True]
        if flags_on and kwargs.get("mode", "normal") == "normal":
            kwargs["mode"] = "accorgimenti"
        return cls(**kwargs)


# Default instance used when the caller passes nothing (== 4.4.0 behaviour).
DEFAULT_PLAN_OPTIONS = PlanOptions()
