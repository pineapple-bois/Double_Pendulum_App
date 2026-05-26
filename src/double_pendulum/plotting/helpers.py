import matplotlib.pyplot as plt
import plotly.tools as tls


def generate_pendulum_figures(pendulum, fig_width, fig_height):
    pendulum.precompute_positions()
    animation = pendulum.animate_pendulum(trace=True, fig_width=fig_width, fig_height=fig_height, static=True)
    matplotlib_phase_fig = pendulum.phase_path()
    phase_fig = tls.mpl_to_plotly(matplotlib_phase_fig)
    phase_fig.update_layout(
        autosize=True,
        margin=dict(l=20, r=20, t=20, b=20),
        width=fig_width,
        height=fig_height,
    )
    plt.close(matplotlib_phase_fig)
    return animation, phase_fig


def set_display_styles(pendulum_count):
    if pendulum_count == "two_pendulums":
        return [{"display": "block"}, {"display": "block"}, {"display": "none"}]
    elif pendulum_count == "three_pendulums":
        return [{"display": "block"}, {"display": "block"}, {"display": "block"}]
    else:
        return [{"display": "none"}, {"display": "none"}, {"display": "none"}]
