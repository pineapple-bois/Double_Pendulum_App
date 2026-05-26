import pytest

from src.double_pendulum.validation import validate_input_sections
from tests.helpers import extract_dash_text


VALID_INITIAL_CONDITIONS = [[0, 120, 0, 0]]
VALID_SIMPLE_PARAMS = (1, 1, 1, 1, 1, 1, 9.81)
VALID_COMPOUND_PARAMS = (1, 1, 1, 1, 1, 1, 9.81)


def validation_messages(
    initial_conditions=VALID_INITIAL_CONDITIONS,
    time_start=0,
    time_end=20,
    model_type="simple",
    params=VALID_SIMPLE_PARAMS,
):
    sections = validate_input_sections(
        initial_conditions,
        time_start,
        time_end,
        model_type,
        *params,
    )
    return [message for section in sections for message in section.messages]


def test_dash_validation_wrapper_renders_validation_messages():
    from src.double_pendulum.validation.dash import validate_inputs

    dash_messages = extract_dash_text(
        validate_inputs(
            [[0, 120, 0, None]],
            0,
            20,
            "simple",
            *VALID_SIMPLE_PARAMS,
        )
    )

    assert "ω2 requires a numerical value." in dash_messages


def test_accepts_representative_simple_inputs():
    assert validation_messages() == []


def test_accepts_representative_compound_inputs():
    assert (
        validation_messages(
            model_type="compound",
            params=VALID_COMPOUND_PARAMS,
        )
        == []
    )


@pytest.mark.parametrize(
    ("time_start", "time_end", "expected_message"),
    [
        (None, 20, "Please provide a value for start time."),
        (0, None, "Please provide a value for end time."),
        (-1, 20, "Time interval must begin at zero."),
        (10, 5, "End time must be greater than start time."),
        (0, -1, "End time must be greater than start time."),
        (0, 121, "Maximum simulation time is 120 seconds."),
    ],
)
def test_rejects_invalid_time_intervals(time_start, time_end, expected_message):
    assert expected_message in validation_messages(time_start=time_start, time_end=time_end)


@pytest.mark.parametrize(
    ("params", "expected_message"),
    [
        ((None, 1, 1, 1, 1, 1, 9.81), "l1 (length of rod 1) requires a numerical value."),
        (("long", 1, 1, 1, 1, 1, 9.81), "l1 (length of rod 1) must be a number."),
        ((0, 1, 1, 1, 1, 1, 9.81), "l1 (length of rod 1) must be between 0.1 and 10."),
        ((11, 1, 1, 1, 1, 1, 9.81), "l1 (length of rod 1) must be between 0.1 and 10."),
        ((1, 0, 1, 1, 1, 1, 9.81), "l2 (length of rod 2) must be between 0.1 and 10."),
    ],
)
def test_rejects_invalid_lengths(params, expected_message):
    assert expected_message in validation_messages(params=params)


@pytest.mark.parametrize(
    ("params", "expected_message"),
    [
        ((1, 1, None, 1, 1, 1, 9.81), "m1 (mass of bob 1) requires a numerical value."),
        ((1, 1, "heavy", 1, 1, 1, 9.81), "m1 (mass of bob 1) must be a number."),
        ((1, 1, 0, 1, 1, 1, 9.81), "m1 (mass of bob 1) must be between 0.1 and 1000."),
        ((1, 1, 1, 1001, 1, 1, 9.81), "m2 (mass of bob 2) must be between 0.1 and 1000."),
    ],
)
def test_rejects_invalid_simple_masses(params, expected_message):
    assert expected_message in validation_messages(params=params)


@pytest.mark.parametrize(
    ("params", "expected_message"),
    [
        ((1, 1, 1, 1, None, 1, 9.81), "M1 (mass of rod 1) requires a numerical value."),
        ((1, 1, 1, 1, "heavy", 1, 9.81), "M1 (mass of rod 1) must be a number."),
        ((1, 1, 1, 1, 0, 1, 9.81), "M1 (mass of rod 1) must be between 0.1 and 1000."),
        ((1, 1, 1, 1, 1, 1001, 9.81), "M2 (mass of rod 2) must be between 0.1 and 1000."),
    ],
)
def test_rejects_invalid_compound_masses(params, expected_message):
    assert expected_message in validation_messages(model_type="compound", params=params)


@pytest.mark.parametrize(
    ("params", "expected_messages"),
    [
        ((1, 1, 1, 1, 1, 1, None), ["g (acceleration due to gravity) requires a numerical value."]),
        ((1, 1, 1, 1, 1, 1, "earth"), ["g (acceleration due to gravity) must be a number."]),
        (
            (1, 1, 1, 1, 1, 1, 0),
            [
                "g (acceleration due to gravity) must be between 0.696 and 23.15.",
                "Note: Pluto's gravity = 0.696 m/s^2, Jupiter's gravity = 23.15 m/s^2",
            ],
        ),
        ((1, 1, 1, 1, 1, 1, 30), ["g (acceleration due to gravity) must be between 0.696 and 23.15."]),
    ],
)
def test_rejects_invalid_gravity(params, expected_messages):
    messages = validation_messages(params=params)
    for expected_message in expected_messages:
        assert expected_message in messages


@pytest.mark.parametrize(
    ("initial_conditions", "expected_message"),
    [
        ([[None, 120, 0, 0]], "θ1 requires a numerical value."),
        ([["a", 120, 0, 0]], "θ1 requires a numerical value."),
        ([[-181, 0, 0, 0]], "θ1 must be between -180 and 180 degrees."),
        ([[181, 0, 0, 0]], "θ1 must be between -180 and 180 degrees."),
        ([[0, -181, 0, 0]], "θ2 must be between -180 and 180 degrees."),
        ([[0, 181, 0, 0]], "θ2 must be between -180 and 180 degrees."),
        ([[0, 120, 1001, 0]], "ω1 must be within ±1000 deg/s."),
        ([[0, 120, -1001, 0]], "ω1 must be within ±1000 deg/s."),
        ([[0, 120, 0, 1001]], "ω2 must be within ±1000 deg/s."),
    ],
)
def test_rejects_invalid_initial_conditions(initial_conditions, expected_message):
    assert expected_message in validation_messages(initial_conditions=initial_conditions)


def test_rejects_multiple_invalid_initial_condition_rows_with_row_labels():
    messages = validation_messages(
        initial_conditions=[
            [0, 120, 0, None],
            [0, 121, 0, None],
            [0, 122, 0, None],
        ]
    )

    assert "Pendulum 1: ω2 requires a numerical value." in messages
    assert "Pendulum 2: ω2 requires a numerical value." in messages
    assert "Pendulum 3: ω2 requires a numerical value." in messages


def test_rejects_bool_and_container_initial_condition_values():
    messages = validation_messages(initial_conditions=[[[], {}, True, "string"]])

    assert "θ1 requires a numerical value." in messages
    assert "θ2 requires a numerical value." in messages
    assert "ω1 requires a numerical value." in messages
    assert "ω2 requires a numerical value." in messages
