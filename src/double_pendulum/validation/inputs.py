from dataclasses import dataclass
import math


MAX_TIME = 60
MAX_LENGTH = 10      # meters
MIN_LENGTH = 0.1     # meters
MAX_MASS = 1000      # kilograms
MIN_MASS = 0.1       # kilograms
MAX_GRAVITY = 23.15  # m/s^2, g on Jupiter
MIN_GRAVITY = 0.696  # m/s^2, g on Pluto
MAX_ANGULAR_VELOCITY = 1000
VALID_MODEL_TYPES = ("simple", "compound")
VALID_SYSTEM_TYPES = ("lagrangian", "hamiltonian")
VALID_INTEGRATOR_POLICIES = (
    "simple_default",
    "simple_reference",
    "solve_ivp_default_baseline",
)


@dataclass(frozen=True)
class ValidationSection:
    title: str
    messages: tuple[str, ...]
    trailing_breaks: int


def validate_input_sections(
    initial_conditions_list,
    time_start,
    time_end,
    model_type,
    param_l1,
    param_l2,
    param_m1,
    param_m2,
    param_M1,
    param_M2,
    param_g,
    system_type,
    integrator_policy_value=None,
):
    sections = []

    configuration_errors = _validate_configuration(
        model_type,
        system_type,
        integrator_policy_value,
    )
    if configuration_errors:
        sections.append(
            ValidationSection(
                "Configuration values:",
                tuple(configuration_errors),
                2,
            )
        )

    param_errors = _validate_parameters(
        model_type,
        param_l1,
        param_l2,
        param_m1,
        param_m2,
        param_M1,
        param_M2,
        param_g,
    )
    if param_errors:
        sections.append(
            ValidationSection("Parameter values:", tuple(param_errors), 2)
        )

    init_cond_errors = _validate_initial_conditions(initial_conditions_list)
    if init_cond_errors:
        sections.append(
            ValidationSection(
                "Initial conditions:",
                tuple(init_cond_errors),
                1,
            )
        )

    time_errors = _validate_time_interval(time_start, time_end)
    if time_errors:
        sections.append(ValidationSection("Time values:", tuple(time_errors), 2))

    return sections


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_finite_number(value):
    return _is_number(value) and math.isfinite(value)


def _validate_configuration(model_type, system_type, integrator_policy_value):
    errors = []
    if model_type not in VALID_MODEL_TYPES:
        errors.append(
            f"Model type must be one of: {', '.join(VALID_MODEL_TYPES)}."
        )
    if system_type not in VALID_SYSTEM_TYPES:
        errors.append(
            f"System type must be one of: {', '.join(VALID_SYSTEM_TYPES)}."
        )
    if (
        integrator_policy_value is not None
        and integrator_policy_value not in VALID_INTEGRATOR_POLICIES
    ):
        errors.append(
            "Integrator policy must be one of: "
            f"{', '.join(VALID_INTEGRATOR_POLICIES)}."
        )
    return errors


def _validate_parameters(
    model_type,
    param_l1,
    param_l2,
    param_m1,
    param_m2,
    param_M1,
    param_M2,
    param_g,
):
    param_errors = []
    param_limits = {
        "l1 (length of rod 1)": (MIN_LENGTH, MAX_LENGTH),
        "l2 (length of rod 2)": (MIN_LENGTH, MAX_LENGTH),
        "m1 (mass of bob 1)": (MIN_MASS, MAX_MASS),
        "m2 (mass of bob 2)": (MIN_MASS, MAX_MASS),
        "M1 (mass of rod 1)": (MIN_MASS, MAX_MASS),
        "M2 (mass of rod 2)": (MIN_MASS, MAX_MASS),
        "g (acceleration due to gravity)": (MIN_GRAVITY, MAX_GRAVITY),
    }

    param_values = {
        "l1 (length of rod 1)": param_l1,
        "l2 (length of rod 2)": param_l2,
        "g (acceleration due to gravity)": param_g,
    }
    if model_type == "simple":
        param_values.update(
            {
                "m1 (mass of bob 1)": param_m1,
                "m2 (mass of bob 2)": param_m2,
            }
        )
    elif model_type == "compound":
        param_values.update(
            {
                "M1 (mass of rod 1)": param_M1,
                "M2 (mass of rod 2)": param_M2,
            }
        )

    for param_name, param_value in param_values.items():
        if param_name in param_limits:
            min_val, max_val = param_limits[param_name]
            if param_value is None:
                param_errors.append(f"{param_name} requires a numerical value.")
            elif not _is_number(param_value):
                param_errors.append(f"{param_name} must be a number.")
            elif not math.isfinite(param_value):
                param_errors.append(f"{param_name} must be finite.")
            elif not (min_val <= param_value <= max_val):
                param_errors.append(f"{param_name} must be between {min_val} and {max_val}.")
                if param_name == "g (acceleration due to gravity)":
                    param_errors.append(
                        f"Note: Pluto's gravity = {MIN_GRAVITY} m/s^2, Jupiter's gravity = {MAX_GRAVITY} m/s^2"
                    )

    return param_errors


def _validate_initial_conditions(initial_conditions_list):
    init_cond_errors = []
    condition_names = ["θ1", "θ2", "ω1", "ω2"]
    multiple_initial_conditions = len(initial_conditions_list) > 1

    for i, conditions in enumerate(initial_conditions_list, start=1):
        pendulum_label = f"Pendulum {i}: " if multiple_initial_conditions else ""
        for name, value in zip(condition_names, conditions):
            if value is None or not _is_number(value):
                init_cond_errors.append(f"{pendulum_label}{name} requires a numerical value.")
            elif not math.isfinite(value):
                init_cond_errors.append(f"{pendulum_label}{name} must be finite.")
            else:
                if name in ["θ1", "θ2"] and (value < -180 or value > 180):
                    init_cond_errors.append(f"{pendulum_label}{name} must be between -180 and 180 degrees.")
                elif name in ["ω1", "ω2"]:
                    if abs(value) > MAX_ANGULAR_VELOCITY:
                        init_cond_errors.append(
                            f"{pendulum_label}{name} must be within ±{MAX_ANGULAR_VELOCITY} deg/s."
                        )

    return init_cond_errors


def _validate_time_interval(time_start, time_end):
    time_errors = []
    if time_start is None:
        time_errors.append("Please provide a value for start time.")
    elif not _is_number(time_start):
        time_errors.append("Start time must be a number.")
    elif not math.isfinite(time_start):
        time_errors.append("Start time must be finite.")

    if time_end is None:
        time_errors.append(f"Please provide an end time from 0 to {MAX_TIME} seconds.")
    elif not _is_number(time_end):
        time_errors.append("End time must be a number.")
    elif not math.isfinite(time_end):
        time_errors.append("End time must be finite.")

    if _is_finite_number(time_start) and _is_finite_number(time_end):
        if time_start >= time_end or time_end <= 0:
            time_errors.append("End time must be greater than start time.")
        if time_start < 0:
            time_errors.append("Time interval must begin at zero.")
        if time_end - time_start > MAX_TIME:
            time_errors.append(f"Maximum simulation time is {MAX_TIME} seconds.")

    return time_errors
