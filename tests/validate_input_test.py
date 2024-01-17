import unittest
from unittest.mock import Mock
from AppFunctions import validate_inputs

# Define MAX_TIME
MAX_TIME = 120

# Define max parameter values
MAX_LENGTH = 10      # meters
MIN_LENGTH = 0.1     # meters
MAX_MASS = 1000      # kilograms
MIN_MASS = 0.1       # kilograms
MAX_GRAVITY = 23.15  # m/s^2, g on Jupiter (2.36 * g_earth)
MIN_GRAVITY = 0.696  # m/s^2, g on Pluto (0.071 * g_earth)


class TestValidateInputs(unittest.TestCase):

    def setUp(self):
        # Mock the html.Br() function from Dash for each test
        self.html = Mock()
        self.html.Br.return_value = ' <br> '

    @staticmethod
    def _extract_error_messages(errors):
        if errors is None:
            return []  # Return an empty list when there are no errors
        # Errors is a list of html.Div objects, each containing a string and an html.Br()
        messages = []
        for error in errors.children:
            # Extract the string part of the error, assuming it's the first element in the contents of the html.Div
            messages.append(str(error))
        return messages

    # time interval test
    def test_time_none(self):
        errors_div = validate_inputs([[0, 120, 0, 0]],
                                 None, 10, 'simple',
                                 1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("Please provide a value for start time.", messages)

        errors_div = validate_inputs([[0, 120, 0, 0]],
                                 0, None, 'simple',
                                 1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("Please provide a value for end time.", messages)

    def test_start_not_negative(self):
        errors_div = validate_inputs([[0, 120, 0, 0]],
                                 -1, 10, 'simple',
                                 1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("Time interval must begin at zero.", messages)

    def test_end_not_negative(self):
        errors_div = validate_inputs([[0, 120, 0, 0]],
                                 0, -1, 'simple',
                                 1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("End time must be greater than start time.", messages)

    def test_greater_than_start(self):
        errors_div = validate_inputs([[0, 120, 0, 0]],
                                 10, 5, 'simple',
                                 1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("End time must be greater than start time.", messages)

    def test_interval_too_long(self):
        errors_div = validate_inputs([[0, 120, 0, 0]],
                                 0, 121, 'simple',
                                 1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn(f"Maximum simulation time is {MAX_TIME} seconds.", messages)

    # Parameter tests
    def test_parameters_none(self):
        # Test for each parameter being None
        # Example for l1 being None
        errors_div = validate_inputs([[0, 120, 0, 0]],
                                     0, 20, 'simple',
                                     None, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("l1 (length of rod 1) is required.", messages)
        # Add similar tests for other parameters

    def test_parameters_non_numeric(self):
        # Test for each parameter being non-numeric
        # Example for l1 being a string
        errors_div = validate_inputs([[0, 120, 0, 0]],
                                     0, 20, 'simple',
                                     'a', 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("l1 (length of rod 1) must be a number.", messages)
        # Add similar tests for other parameters

    def test_parameters_out_of_range(self):
        # Test for each parameter being out of range
        # Example for l1 being too low
        errors_div = validate_inputs([[0, 120, 0, 0]],
                                     0, 20, 'simple',
                                     0, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("l1 (length of rod 1) must be between 0.1 and 10.", messages)
        # Add similar tests for other parameters being too low or too high

    def test_valid_parameters(self):
        # Test for all parameters being valid
        errors_div = validate_inputs([[0, 120, 0, 0]],
                                     0, 20, 'simple',
                                     1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertEqual(len(messages), 0)  # No error messages expected

    def test_gravity_parameter(self):
        # Test for gravity being out of range
        # Example for g being too low
        errors_div = validate_inputs([[0, 120, 0, 0]],
                                     0, 20, 'simple',
                                     1, 1, 1, 1, 1, 1, 0)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("g (acceleration due to gravity) must be between 0.696 and 23.15.", messages)

        # Example for g being too high
        errors_div = validate_inputs([[0, 120, 0, 0]],
                                     0, 20, 'simple',
                                     1, 1, 1, 1, 1, 1, 30)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("g (acceleration due to gravity) must be between 0.696 and 23.15.", messages)

        # Example for g being None
        errors_div = validate_inputs([[0, 120, 0, 0]],
                                     0, 20, 'simple',
                                     1, 1, 1, 1, 1, 1, None)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("g (acceleration due to gravity) is required.", messages)

        # Example for g being non-numeric
        errors_div = validate_inputs([[0, 120, 0, 0]],
                                     0, 20, 'simple',
                                     1, 1, 1, 1, 1, 1, 'a')
        messages = self._extract_error_messages(errors_div)
        self.assertIn("g (acceleration due to gravity) must be a number.", messages)

    # Initial conditions test
    def test_initial_conditions_none(self):
        # Test for one of the initial conditions being None
        errors_div = validate_inputs([[None, 120, 0, 0]],
                                     0, 20, 'simple',
                                     1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("Pendulum A: θ1 requires a numerical value.", messages)

    def test_initial_conditions_non_numeric(self):
        # Test for one of the initial conditions being non-numeric
        errors_div = validate_inputs([['a', 120, 0, 0]],
                                     0, 20, 'simple',
                                     1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("Pendulum A: θ1 requires a numerical value.", messages)

    def test_initial_conditions_valid(self):
        # Test for all initial conditions being valid
        errors_div = validate_inputs([[0, 120, 0, 0]],
                                     0, 20, 'simple',
                                     1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertEqual(len(messages), 0)  # No error messages expected

    def test_mixed_valid_invalid_initial_conditions(self):
        errors_div = validate_inputs([[0, 120, 0, None], [0, 121, 0, None], [0, 122, 0, None]],
                                     0, 20, 'simple', 1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("Pendulum A: ω2 requires a numerical value.", messages)
        self.assertIn("Pendulum B: ω2 requires a numerical value.", messages)
        self.assertIn("Pendulum C: ω2 requires a numerical value.", messages)

    def test_initial_conditions_different_non_numeric_types(self):
        errors_div = validate_inputs([[[], {}, True, 'string']],
                                     0, 20, 'simple', 1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("Pendulum A: θ1 requires a numerical value.", messages)
        self.assertIn("Pendulum A: θ2 requires a numerical value.", messages)
        self.assertIn("Pendulum A: ω1 requires a numerical value.", messages)
        self.assertIn("Pendulum A: ω2 requires a numerical value.", messages)

    def test_extreme_angular_velocity(self):
        errors_div = validate_inputs([[0, 120, 300000, 0]],
                                     0, 20, 'simple',
                                     1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("Pendulum A: ω1 must be less than 1000 deg/s.", messages)

        errors_div = validate_inputs([[0, 120, -300000, 0]],
                                     0, 20, 'simple',
                                     1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("Pendulum A: ω1 must be greater than -1000 deg/s.", messages)

    def test_theta_range(self):
        # Test for θ being too low
        errors_div = validate_inputs([[-361, 0, 0, 0]],
                                     0, 20, 'simple',
                                     1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("Pendulum A: θ1 must be between -180 and 180 degrees.", messages)

        # Test for θ being too high
        errors_div = validate_inputs([[361, 0, 0, 0]],
                                     0, 20, 'simple',
                                     1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertIn("Pendulum A: θ1 must be between -180 and 180 degrees.", messages)

        # Test for valid θ value
        errors_div = validate_inputs([[180, 0, 0, 0]],
                                     0, 20, 'simple',
                                     1, 1, 1, 1, 1, 1, 9.81)
        messages = self._extract_error_messages(errors_div)
        self.assertEqual(len(messages), 0)  # No error messages expected for valid θ value


if __name__ == '__main__':
    unittest.main()






