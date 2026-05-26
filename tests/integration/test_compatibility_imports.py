def test_app_function_helpers_are_importable_from_source_package():
    from src.double_pendulum.app_functions import generate_pendulum_figures, set_display_styles
    from src.double_pendulum.validation.dash import validate_inputs

    assert callable(validate_inputs)
    assert callable(generate_pendulum_figures)
    assert callable(set_display_styles)


def test_math_helpers_are_importable_from_source_package():
    from src.double_pendulum.math import form_lagrangian, l1, theta1

    assert callable(form_lagrangian)
    assert str(l1) == "l1"
    assert str(theta1) == "theta1(t)"


def test_model_classes_are_importable_from_source_package():
    from src.double_pendulum.models import DoublePendulumHamiltonian, DoublePendulumLagrangian

    assert DoublePendulumHamiltonian.__name__ == "DoublePendulumHamiltonian"
    assert DoublePendulumLagrangian.__name__ == "DoublePendulumLagrangian"
