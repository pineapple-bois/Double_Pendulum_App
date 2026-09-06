"""Pure semantics for the supported long-horizon first-flip representation.

This module classifies already-computed trusted-policy outcomes.  It does not
import or invoke dynamics, solvers, field generation, or persistence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Sequence


LONG_HORIZON_HAT = 10_000.0


class FirstFlipLogarithmicClass(str, Enum):
    """Learner-facing classes supported by the long-horizon scaffold."""

    TAU_HAT_LT_1 = "tau_hat_lt_1"
    TAU_HAT_1_TO_10 = "tau_hat_1_to_10"
    TAU_HAT_10_TO_100 = "tau_hat_10_to_100"
    TAU_HAT_100_TO_1000 = "tau_hat_100_to_1000"
    TAU_HAT_1000_TO_10000 = "tau_hat_1000_to_10000"
    NO_FLIP_OBSERVED_BY_H10000 = "no_flip_observed_by_h10000"
    ENERGY_INACCESSIBLE = "energy_inaccessible"
    NUMERICALLY_UNRESOLVED = "numerically_unresolved"


LOGARITHMIC_CLASS_ORDER = tuple(FirstFlipLogarithmicClass)


class TrustedPolicyOutcomeStatus(str, Enum):
    """Usable outcome vocabulary supplied by one trusted numerical policy."""

    EVENT_OBSERVED = "event_observed"
    RIGHT_CENSORED = "right_censored"
    NUMERICALLY_INVALID = "numerically_invalid"


@dataclass(frozen=True)
class TrustedPolicyFirstFlipOutcome:
    """One already-computed policy result at the supported long horizon."""

    policy: str
    status: TrustedPolicyOutcomeStatus
    dimensionless_event_time: float | None = None

    def __post_init__(self) -> None:
        if not self.policy.strip():
            raise ValueError("policy must be a nonempty identifier")
        if not isinstance(self.status, TrustedPolicyOutcomeStatus):
            raise TypeError("status must be a TrustedPolicyOutcomeStatus")
        if self.status is TrustedPolicyOutcomeStatus.EVENT_OBSERVED:
            if self.dimensionless_event_time is None:
                raise ValueError("an observed event requires dimensionless_event_time")
            value = float(self.dimensionless_event_time)
            if not math.isfinite(value) or value <= 0.0 or value > LONG_HORIZON_HAT:
                raise ValueError(
                    "dimensionless_event_time must be finite and inside (0, 10000]"
                )
        elif self.dimensionless_event_time is not None:
            raise ValueError("censored or invalid outcomes cannot carry an event time")


def logarithmic_class_for_event_time(
    dimensionless_event_time: float,
) -> FirstFlipLogarithmicClass:
    """Classify an event time using half-open decades and strict cap semantics.

    Boundaries 1, 10, 100, and 1000 enter the decade beginning at that value.
    Equality at 10000 is assigned to no-event-by-horizon, matching the
    authoritative capped-field convention that only events strictly before a
    horizon count as observed by that horizon.
    """

    value = float(dimensionless_event_time)
    if not math.isfinite(value) or value <= 0.0 or value > LONG_HORIZON_HAT:
        raise ValueError("dimensionless event time must be finite and in (0, 10000]")
    if value < 1.0:
        return FirstFlipLogarithmicClass.TAU_HAT_LT_1
    if value < 10.0:
        return FirstFlipLogarithmicClass.TAU_HAT_1_TO_10
    if value < 100.0:
        return FirstFlipLogarithmicClass.TAU_HAT_10_TO_100
    if value < 1000.0:
        return FirstFlipLogarithmicClass.TAU_HAT_100_TO_1000
    if value < LONG_HORIZON_HAT:
        return FirstFlipLogarithmicClass.TAU_HAT_1000_TO_10000
    return FirstFlipLogarithmicClass.NO_FLIP_OBSERVED_BY_H10000


def zero_velocity_energy_inaccessible(theta1: float, theta2: float) -> bool:
    """Apply the validated unit/equal-link zero-velocity energy criterion.

    For this exact simple system, ``E0 < -g`` is equivalent to
    ``2*cos(theta1) + cos(theta2) > 1``.  The strict inequality proves that
    neither arm can complete the defined net revolution.  Equality remains
    energy-accessible, and accessibility is necessary rather than sufficient.
    """

    first = float(theta1)
    second = float(theta2)
    if not math.isfinite(first) or not math.isfinite(second):
        raise ValueError("initial angles must be finite")
    return 2.0 * math.cos(first) + math.cos(second) > 1.0


def policy_logarithmic_class(
    outcome: TrustedPolicyFirstFlipOutcome,
) -> FirstFlipLogarithmicClass:
    """Convert one usable policy outcome to its learner-facing class."""

    if outcome.status is TrustedPolicyOutcomeStatus.NUMERICALLY_INVALID:
        return FirstFlipLogarithmicClass.NUMERICALLY_UNRESOLVED
    if outcome.status is TrustedPolicyOutcomeStatus.RIGHT_CENSORED:
        return FirstFlipLogarithmicClass.NO_FLIP_OBSERVED_BY_H10000
    assert outcome.dimensionless_event_time is not None
    return logarithmic_class_for_event_time(outcome.dimensionless_event_time)


def consensus_logarithmic_class(
    outcomes: Sequence[TrustedPolicyFirstFlipOutcome],
    *,
    rigorously_energy_inaccessible: bool,
) -> FirstFlipLogarithmicClass:
    """Return the unanimous class or an explicit unresolved result.

    No policy is preferred.  A numerically invalid policy, event/censoring
    disagreement, or decade disagreement is unresolved.  A rigorous energy
    classification supersedes unanimous ordinary censoring, but an event in a
    supposedly inaccessible cell is a contract contradiction and is therefore
    unresolved rather than hidden by the energy mask.
    """

    if not outcomes:
        raise ValueError("at least one trusted-policy outcome is required")
    policies = [outcome.policy for outcome in outcomes]
    if len(policies) != len(set(policies)):
        raise ValueError("trusted-policy identifiers must be unique")

    classes = tuple(policy_logarithmic_class(outcome) for outcome in outcomes)
    if FirstFlipLogarithmicClass.NUMERICALLY_UNRESOLVED in classes:
        return FirstFlipLogarithmicClass.NUMERICALLY_UNRESOLVED

    if rigorously_energy_inaccessible:
        if all(
            value is FirstFlipLogarithmicClass.NO_FLIP_OBSERVED_BY_H10000
            for value in classes
        ):
            return FirstFlipLogarithmicClass.ENERGY_INACCESSIBLE
        return FirstFlipLogarithmicClass.NUMERICALLY_UNRESOLVED

    if len(set(classes)) == 1:
        return classes[0]
    return FirstFlipLogarithmicClass.NUMERICALLY_UNRESOLVED


def classify_zero_velocity_consensus(
    theta1: float,
    theta2: float,
    outcomes: Sequence[TrustedPolicyFirstFlipOutcome],
) -> FirstFlipLogarithmicClass:
    """Classify one cell using the validated energy rule and policy consensus."""

    return consensus_logarithmic_class(
        outcomes,
        rigorously_energy_inaccessible=zero_velocity_energy_inaccessible(
            theta1, theta2
        ),
    )


__all__ = [
    "LONG_HORIZON_HAT",
    "LOGARITHMIC_CLASS_ORDER",
    "FirstFlipLogarithmicClass",
    "TrustedPolicyFirstFlipOutcome",
    "TrustedPolicyOutcomeStatus",
    "classify_zero_velocity_consensus",
    "consensus_logarithmic_class",
    "logarithmic_class_for_event_time",
    "policy_logarithmic_class",
    "zero_velocity_energy_inaccessible",
]
