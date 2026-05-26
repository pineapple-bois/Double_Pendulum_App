def test_root_appfunctions_wrapper_exports_existing_helpers():
    from AppFunctions import generate_pendulum_figures, set_display_styles, validate_inputs

    assert callable(validate_inputs)
    assert callable(generate_pendulum_figures)
    assert callable(set_display_styles)


def test_root_mathfunctions_wrapper_exports_existing_symbols():
    from MathFunctions import form_lagrangian, l1, theta1

    assert callable(form_lagrangian)
    assert str(l1) == "l1"
    assert str(theta1) == "theta1(t)"


def test_root_model_wrappers_export_existing_classes():
    from DoublePendulumHamiltonian import DoublePendulumHamiltonian
    from DoublePendulumLagrangian import DoublePendulumLagrangian

    assert DoublePendulumHamiltonian.__name__ == "DoublePendulumHamiltonian"
    assert DoublePendulumLagrangian.__name__ == "DoublePendulumLagrangian"
