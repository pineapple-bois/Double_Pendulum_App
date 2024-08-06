# Main page layout
from dash import html
from dash import dcc

# Plotly figure configuration
# 'displayModeBar': False - removes everything
config = {'displaylogo': False, 'modeBarButtonsToRemove': ['select2d', 'lasso2d']}


def get_navbar():
    return html.Div(
        className="navbar",
        children=[
            html.Div(
                html.Button("Toggle Dark Mode", id="theme-toggle-button", className="nav-button"),
                className="nav-button-container"
            ),
            html.Div(
                children=[
                    dcc.Link("Home", href="/", className="nav-link"),
                    dcc.Link("Mathematics", href="/mathematics", className="nav-link"),
                    dcc.Link("Chaos", href="/chaos", className="nav-link")
                ],
                className="nav-links-container"
            )
        ]
    )


def get_title_section():
    return html.Div(
        className="title-section",
        children=[
            html.H1("Double Pendulum Simulation", className="title-text"),
            html.P([
                dcc.Markdown('''
                    Both pendulums move in the $(x,y)$-plane. The system has two degrees of freedom, 
                    uniquely determined by the values of $\\theta_1$ & $\\theta_2$
                    ''', mathjax=True, className="subtitle-text"),
            ], className="title-description")
        ]
    )


def get_description_images_section():
    return html.Div(
        className="description-images-section",
        children=[
            html.Div(
                className="description",
                children=[
                    html.H3("Description", className="description-title"),
                    html.P("The double pendulum is an archetypal non-linear system in classical mechanics that has been studied since the 18th century.", className="description-text"),
                    html.P(
                        [
                            "We model two types of double pendulum; simple and compound. Coupled, ordinary differential equations of motion are derived in accordance with both Lagrangian and Hamiltonian formalism. Detailed descriptions of the derivations can be found on the ",
                            html.A("mathematics", href="/mathematics", className="description-link"),
                            " page."
                        ],
                        className="description-text"
                    ),
                    html.P("Motion of a double pendulum system is characterised by extreme sensitivity to initial conditions, exhibiting both periodic and chaotic behaviour. This simulation provides a rich context for exploring these non-linear dynamics.", className="description-text"),
                    html.P("We generate a time graph, phase portrait, and animation based on the selected model parameters including release angle and angular velocity. Interesting dynamics can be discovered by simply releasing the pendulums from rest.", className="description-text"),
                    html.P(
                        [
                            "The acceleration due to gravity is the restoring force that influences the oscillation period and stability of the motion. This model allows simulation of the pendulum's behaviour on different ",
                            html.A("celestial bodies in our Solar System", href="https://nssdc.gsfc.nasa.gov/planetary/factsheet/planet_table_ratio.html", className="description-link"),
                            "."
                        ],
                        className="description-text"
                    ),
                    html.P("Select the type of pendulum system to model and derivation formalism below.", className="description-instruction")
                ]
            ),
            html.Div(
                className="simple-model",
                children=[
                    html.H3("Simple Model", className="model-title"),
                    dcc.Markdown('''
                        Rigid, massless, and inextensible rods $OP_1$ and $P_{1}P_{2}$ are connected by a frictionless hinge to point masses; $m_1$ & $m_2$.
                    ''', mathjax=True, className="model-description"),
                    html.Img(src='/assets/Model_Simple_Transparent_NoText.png', className="model-image")
                ]
            ),
            html.Div(
                className="compound-model",
                children=[
                    html.H3("Compound Model", className="model-title"),
                    dcc.Markdown('''
                        The rods are modeled as [uniform thin rods](https://phys.libretexts.org/Courses/Joliet_Junior_College/Physics_201_-_Fall_2019v2/Book%3A_Custom_Physics_textbook_for_JJC/11%3A_Rotational_Kinematics_Angular_Momentum_and_Energy/11.06%3A_Calculating_Moments_of_Inertia) of evenly distributed masses; $M_1$ & $M_2$.
                    ''', mathjax=True, className="model-description"),
                    html.Img(src='/assets/Model_Compound_Transparent_NoText.png', className="model-image")
                ]
            )
        ]
    )


def get_main_content_section():
    return html.Div(
        className="main-content-section",
        children=[
            html.Div(
                className="inputs",
                children=[
                    html.Div(className='input-group model-system-group', children=[
                        html.Label('Model Type:', className='label model-type-label'),
                        dcc.Dropdown(
                            id='model-type',
                            options=[
                                {'label': 'Simple', 'value': 'simple'},
                                {'label': 'Compound', 'value': 'compound'}
                            ],
                            value='simple',
                            clearable=False,
                            className='dropdown model-system-dropdown'
                        ),
                        html.Label('System Type:', className='label system-type-label'),
                        dcc.Dropdown(
                            id='system-type',
                            options=[
                                {'label': 'Lagrangian', 'value': 'lagrangian'},
                                {'label': 'Hamiltonian', 'value': 'hamiltonian'}
                            ],
                            value='lagrangian',
                            clearable=False,
                            className='dropdown system-type-dropdown'
                        ),
                    ]),
                    html.Div(className='container-buttons unity-parameters-group', children=[
                        html.Label('Set masses to 1kg and lengths to 1m:', className='label model-type-label'),
                        html.Button('Set Unity Parameters', id='unity-parameters', n_clicks=0, className='button unity-parameters-button'),
                    ]),
                    html.Div(className='input-group parameters-group', children=[
                        html.Label('Parameters (l1, l2, m1, m2, M1, M2, g)', id='parameters-label', className='label parameters-label'),
                        dcc.Input(id='param_l1', type='number', placeholder='l1 (length of rod 1)', className='input parameters-input'),
                        dcc.Input(id='param_l2', type='number', placeholder='l2 (length of rod 2)', className='input parameters-input'),
                        dcc.Input(id='param_m1', type='number', placeholder='m1 (mass of bob 1)', className='input parameters-input'),
                        dcc.Input(id='param_m2', type='number', placeholder='m2 (mass of bob 2)', className='input parameters-input'),
                        dcc.Input(id='param_M1', type='number', placeholder='M1 (mass of rod 1)', className='input parameters-input', style={'display': 'none'}),
                        dcc.Input(id='param_M2', type='number', placeholder='M2 (mass of rod 2)', className='input parameters-input', style={'display': 'none'}),
                        dcc.Dropdown(
                            id='param_g',
                            options=[
                                {'label': 'Mercury: 3.7 m/s²', 'value': 3.7},
                                {'label': 'Venus: 8.87 m/s²', 'value': 8.87},
                                {'label': 'Earth: 9.81 m/s²', 'value': 9.81},
                                {'label': 'Moon: 1.62 m/s²', 'value': 1.62},
                                {'label': 'Mars: 3.71 m/s²', 'value': 3.71},
                                {'label': 'Jupiter: 23.15 m/s²', 'value': 23.15},
                                {'label': 'Saturn: 10.44 m/s²', 'value': 10.44},
                                {'label': 'Uranus: 8.69 m/s²', 'value': 8.69},
                                {'label': 'Neptune: 11.15 m/s²', 'value': 11.15},
                                {'label': 'Pluto: 0.696 m/s²', 'value': 0.696},
                            ],
                            value=9.81,
                            placeholder='Acceleration due to gravity, m/s²',
                            clearable=False,
                            searchable=False,
                            className='dropdown parameters-dropdown'
                        )
                    ]),
                    html.Div(className='input-group initial-conditions-group', children=[
                        html.Label('Initial Conditions (θ1, θ2, ω1, ω2): degrees', className='label initial-conditions-label'),
                        dcc.Input(id='init_cond_theta1', type='number', placeholder='Angle 1', className='input initial-conditions-input'),
                        dcc.Input(id='init_cond_theta2', type='number', placeholder='Angle 2', className='input initial-conditions-input'),
                        dcc.Input(id='init_cond_omega1', type='number', placeholder='Angular velocity 1', className='input initial-conditions-input'),
                        dcc.Input(id='init_cond_omega2', type='number', placeholder='Angular velocity 2', className='input initial-conditions-input'),
                    ]),
                    html.Div(className='input-group time-vector-group', children=[
                        html.Label('Time Vector (start, stop): seconds', className='label time-vector-label'),
                        dcc.Input(id='time_start', type='number', placeholder='Start Time', value=0, className='input time-vector-input'),
                        dcc.Input(id='time_end', type='number', placeholder='End Time', value=20, className='input time-vector-input'),
                    ]),
                    html.Div(className='container-buttons run-simulation-group', children=[
                        html.Button('Run Simulation', id='submit-val', n_clicks=0, className='button run-simulation-button'),
                    ]),
                ]
            ),
            html.Div(
                className="main-content",
                children=[
                    dcc.Loading(
                        id="loading-1",
                        type="default",  # or "circle", "dot", or "cube" for different spinner types
                        children=[
                            html.Div(
                                id='animation-phase-container',
                                className='graph-row',
                                style={'display': 'none'},
                                children=[
                                    html.Div(
                                        dcc.Graph(id='pendulum-animation', config=config, className='responsive-graph'),
                                        className='graph-column'
                                    ),
                                    html.Div(
                                        dcc.Graph(id='phase-graph', config=config, className='responsive-graph'),
                                        className='graph-column'
                                    )
                                ]
                            ),
                            html.Div(
                                id='time-graph-container',
                                className='graph-container',
                                style={'display': 'none'},
                                children=[
                                    dcc.Graph(id='time-graph', responsive=True, className='responsive-graph')
                                ]
                            )
                        ],
                        style={'height': '100%', 'position': 'relative'}
                    ),
                    html.Div(id='error-message', className='error-message')
                ]
            )
        ]
    )


def get_footer_section():
    return html.Div(
        children=[
            html.Img(src="assets/github-mark.png", className='info-image', style={'width': '30px'}),
            html.Div(
                children=[
                    html.Span("The Double Pendulum application was built from this ", className='info-text'),
                    dcc.Link("GitHub Repository", href="https://github.com/pineapple-bois/Double_Pendulum_App", target="_blank", className='info-link'),
                    html.Div("© pineapple-bois 2024", className='info-footer')
                ],
                style={'flexDirection': 'column'}
            )
        ],
        className='info-container',
        style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'flex-start', 'padding': '1rem', 'background': '#f8f9fa'}
    )


def get_main_layout():
    return html.Div(
        className='main-layout',
        children=[
            get_navbar(),
            get_title_section(),
            get_description_images_section(),
            get_main_content_section(),
            get_footer_section()
        ]
    )
