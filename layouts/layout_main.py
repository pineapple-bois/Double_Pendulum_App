# Main page layout
from dash import html
from dash import dcc

# Plotly figure configuration
# 'displayModeBar': False - removes everything
config = {'displaylogo': False, 'modeBarButtonsToRemove': ['select2d', 'lasso2d']}

with open('assets/information.txt', 'r') as file:
    information_text = file.read()


# GitHub logo
def github_logo():
    return html.Img(src="assets/Images/github-mark.png",
                    className='info-image',
                    style={'width': '30px'}
                    )


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
                    dcc.Link("Lagrangian", href="/lagrangian", className="nav-link"),
                    dcc.Link("Hamiltonian", href="/hamiltonian", className="nav-link"),
                    dcc.Link("Chaos", href="/chaos", className="nav-link")
                ],
                className="nav-links-container"
            )
        ]
    )


def get_title_section(text):
    return html.Div(
        className="title-section",
        children=[
            html.H1(text, className="title-text"),
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
                    html.P([
                               "The double pendulum is an archetypal non-linear system in classical mechanics that has "
                               "been studied since the 18th century. ",
                               "In this simulation, we model two types of double pendulum; simple and compound. ",
                               dcc.Markdown('''
                                Both pendulums move in the $(x,y)$-plane. The system has two degrees of freedom, 
                                uniquely determined by the values of $\\theta_1$ & $\\theta_2$.
                                ''', mathjax=True, style={'display': 'inline'}),
                               ],
                           className="description-text"),
                    html.P([
                               "Motion of a double pendulum system is characterised by extreme sensitivity to initial "
                               "conditions, resulting in both periodic and chaotic behaviour. ",
                               dcc.Markdown('''
                               No closed-form solutions for $\\theta_1$ and $\\theta_2$ as 
                               functions of time are known. Therefore, the system must be solved numerically. 
                               ''', mathjax=True, style={'display': 'inline'}),
                               "The system's equations of motion are derived using both ",
                               html.A("Lagrangian", href="/lagrangian", className="description-link",
                                      target="_blank"),
                               " and ",
                               html.A("Hamiltonian", href="/hamiltonian", className="description-link",
                                      target="_blank"),
                               " formalisms."
                               ],
                           className="description-text"),
                    html.P([
                               "This simulation provides a rich context for exploring non-linear dynamics. "
                               "We generate a time graph, phase portrait, and animation based on the selected model "
                               "parameters including; mass, length, release angle, and angular velocity. "
                               "Fascinating dynamics can be discovered by simply releasing the pendulums from rest. "
                               "The acceleration due to gravity acts as the restoring force, influencing the oscillation "
                               "period and stability of the motion. This model allows for the simulation of pendulum "
                               "behaviour on different ",
                               html.A("celestial bodies in our Solar System",
                                      href="https://nssdc.gsfc.nasa.gov/planetary/factsheet/planet_table_ratio.html",
                                      className="description-link", target="_blank"),
                               "."
                               ],
                           className="description-text"
                           )
                ]
            ),
            html.Div(  # New parent container for both models
                className="models-container",
                children=[
                    html.Div(
                        className="simple-model",
                        children=[
                            html.Div(
                                className="image-description",
                                children=[
                                    html.H3("Simple Model", className="model-title"),
                                    dcc.Markdown('''
                                        Rigid, massless, and inextensible rods $OP_1$ and $P_{1}P_{2}$ are connected by a frictionless hinge to point masses; $m_1$ & $m_2$.
                                    ''', mathjax=True, className="model-description")
                                ],
                            ),
                            html.Div(
                                className="image-container",
                                children=[
                                    html.Img(src='/assets/Images/Model_Simple_Transparent_NoText.png', className="model-image")
                                ]
                            )
                        ]
                    ),
                    html.Div(
                        className="compound-model",
                        children=[
                            html.Div(
                                className="image-description",
                                children=[
                                    html.H3("Compound Model", className="model-title"),
                                    dcc.Markdown('''
                                        The rods are modeled as [uniform thin rods](https://phys.libretexts.org/Courses/Joliet_Junior_College/Physics_201_-_Fall_2019v2/Book%3A_Custom_Physics_textbook_for_JJC/11%3A_Rotational_Kinematics_Angular_Momentum_and_Energy/11.06%3A_Calculating_Moments_of_Inertia) of evenly distributed masses $M_1$ & $M_2$ with friction neglected at the hinge.
                                    ''', mathjax=True, className="model-description")],
                            ),
                            html.Div(
                                className="image-container",
                                children=[html.Img(src='/assets/Images/Model_Compound_Transparent_NoText.png',
                                                   className="model-image")]
                            ),
                        ]
                    )
                ]
            )
        ]
    )


def get_main_content_section():
    return html.Div(
        id="scroll-target",
        className="main-content-section",
        children=[
            html.Div(
                className="inputs",
                children=[
                    html.Div(
                        id="info-popup",
                        children=[
                            html.Button("Close Information", id="close-info-button", n_clicks=0,
                                        className="button close-info-button"),
                            dcc.Markdown(information_text, mathjax=True, className="information-content"),
                        ],
                        className="information-container",
                        style={'display': 'none'}
                    ),
                    html.Div(className='input-group model-system-group', children=[
                        html.H4("Model and System Selection", className='inputs-title'),
                        html.Button("What do I even choose?", id="info-button", n_clicks=0,
                                    className="button get-info-button"),
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
                    html.Div(className='input-group parameters-group', children=[
                        html.H4("Parameter Selection", className='inputs-title'),
                        dcc.Markdown(
                            '''Unity Parameters sets masses to $1 \ \\text{kg}$ and lengths to $1 \ \\text{m}$:''',
                            mathjax=True, className="input-subtext parameter-text"),
                        html.Button('Set Unity Parameters', id='unity-parameters', n_clicks=0,
                                    className='button unity-parameters-button'),
                        html.Label('Parameters (l1, l2, m1, m2, M1, M2, g)', id='parameters-label',
                                   className='label parameters-label'),
                        dcc.Input(id='param_l1', type='number', placeholder='l1 (length of rod 1)',
                                  className='input parameters-input'),
                        dcc.Input(id='param_l2', type='number', placeholder='l2 (length of rod 2)',
                                  className='input parameters-input'),
                        dcc.Input(id='param_m1', type='number', placeholder='m1 (mass of bob 1)',
                                  className='input parameters-input'),
                        dcc.Input(id='param_m2', type='number', placeholder='m2 (mass of bob 2)',
                                  className='input parameters-input'),
                        dcc.Input(id='param_M1', type='number', placeholder='M1 (mass of rod 1)',
                                  className='input parameters-input', style={'display': 'none'}),
                        dcc.Input(id='param_M2', type='number', placeholder='M2 (mass of rod 2)',
                                  className='input parameters-input', style={'display': 'none'}),
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
                        ),
                    ]),
                    html.Div(className='input-group initial-conditions-group', children=[
                        html.H4("Initial Conditions", className='inputs-title'),
                        dcc.Markdown(
                            '''The initial angles; $\\theta_1$ & $\\theta_2$ are measured counterclockwise in degrees. A negative angle gives clockwise rotation.''',
                            mathjax=True, className="input-subtext init-condition-text"),
                        html.Label('Initial Conditions (θ1, θ2, ω1, ω2): degrees',
                                   className='label initial-conditions-label'),
                        dcc.Input(id='init_cond_theta1', type='number', placeholder='θ1 (Angle 1)',
                                  className='input initial-conditions-input'),
                        dcc.Input(id='init_cond_theta2', type='number', placeholder='θ2 (Angle 2)',
                                  className='input initial-conditions-input'),
                        dcc.Input(id='init_cond_omega1', type='number', placeholder='ω1 (Angular velocity 1)',
                                  className='input initial-conditions-input'),
                        dcc.Input(id='init_cond_omega2', type='number', placeholder='ω2 (Angular velocity 2)',
                                  className='input initial-conditions-input'),
                    ]),
                    html.Div(className='input-group time-vector-group', children=[
                        html.H4("Time Settings", className='inputs-title'),
                        dcc.Markdown(
                            '''The default time interval is $20$ seconds. The maximum is $120$ seconds.''',
                            mathjax=True, className="input-subtext time-vector-text"),
                        html.Label('Time Vector (start, stop): seconds', className='label time-vector-label'),
                        dcc.Input(id='time_start', type='number', placeholder='Start Time', value=0,
                                  className='input time-vector-input'),
                        dcc.Input(id='time_end', type='number', placeholder='End Time', value=20,
                                  className='input time-vector-input'),
                    ]),
                ]
            ),
            html.Div(
                className="main-content",
                children=[
                    html.Div(
                        className="loading-container",
                        children=[
                            dcc.Loading(
                                id="loading-1",
                                type="cube",  # "default", "circle", "dot", or "cube" for different spinner types
                                children=[
                                    html.Div(id='animation-phase-container', className='above-graph-container',
                                             style={'display': 'none'},
                                             children=[
                                                 dcc.Graph(id='pendulum-animation', config=config,
                                                           className='responsive-graph'),
                                                 dcc.Graph(id='phase-graph', config=config,
                                                           className='responsive-graph')
                                             ]),
                                    html.Div(id='time-graph-container', className='graph-container',
                                             style={'display': 'none'},
                                             children=[
                                                 dcc.Graph(id='time-graph', className='responsive-graph',
                                                           responsive=True)
                                             ]),
                                    html.Div(id='error-message', className='error-message')
                                ],
                                className="delayed-spinner"
                            )
                        ],
                        style={'height': '100%', 'position': 'relative'}
                    ),
                ]
            )
        ]
    )


def get_common_footer(include_button=False, page_type="main"):
    children = []

    # Optionally add the Run Simulation button
    if include_button:
        children.append(
            html.Div(
                className='container-buttons run-simulation-group',
                children=[
                    html.Button('Run Simulation', id='submit-val', n_clicks=0,
                                className='button run-simulation-button'),
                ]
            )
        )

    # Add the Repo section
    children.append(
        html.Div(
            className='footer-text-box',
            children=[
                github_logo(),
                html.Div(
                    children=[
                        html.Span("The Double Pendulum application was built from this", className='info-text'),
                        dcc.Link("GitHub Repository", href="https://github.com/pineapple-bois/Double_Pendulum_App",
                                 target="_blank", className='info-link'),
                        html.Div("© pineapple-bois 2024", className='info-footer')
                    ],
                )
            ]
        )
    )

    # Assign a specific class based on the page type
    footer_class = f'footer-bar {page_type}-page'

    return html.Div(
        className=footer_class,
        children=children
    )


def get_footer_section_main():
    return get_common_footer(include_button=True, page_type="main")


def get_footer_section():
    return get_common_footer(include_button=False, page_type="other")


def get_main_layout():
    return html.Div(
        className='main-layout',
        children=[
            html.Div(
                className='header',
                children=[
                    get_navbar(),
                ]
            ),
            html.Div(
                className='body',
                children=[
                    get_title_section("Double Pendulum Simulation"),
                    get_description_images_section(),
                    get_main_content_section(),
                ]
            ),
            html.Div(
                className='footer',
                children=[
                    get_footer_section_main()
                ]
            ),
        ]
    )
