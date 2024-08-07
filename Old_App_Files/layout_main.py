# Main page layout
from dash import html
from dash import dcc

# Plotly figure configuration
# 'displayModeBar': False - removes everything
config = {'displaylogo': False, 'modeBarButtonsToRemove': ['select2d', 'lasso2d']}


def get_main_layout():
    # This function returns the layout of the main page
    return html.Div([
        # Flex container for the title, chaos page link, and GitHub logo
        html.Div([
            # Link to the chaos page with text on two lines, allow it to shrink on small screens
            html.Div([
                html.A(["Chaotic", html.Br(), "Dynamics"],
                       className="title-link",
                       href="/chaos",
                       style={'fontSize': '20px', 'padding': '10px'}),
            ], style={'flex': '0 1 auto', 'alignSelf': 'center'}),

            # Title, which should stay centered with auto margins
            html.Div([
                html.H1([
                    html.Div("Double Pendulum Simulation", style={'white-space': 'nowrap'}),
                ], style={'textAlign': 'center', 'color': 'black', 'margin': 'auto'})
            ], style={'flex': '1 0 auto', 'minWidth': '0', 'textAlign': 'center'}),
            # minWidth: 0 ensures shrinkage if necessary

            # GitHub logo as a link, allow it to shrink on small screens
            html.Div([
                html.A([
                    html.Img(src='assets/Images/github-mark.png', style={'height': '50px', 'width': '50px'})
                ], className='title-link', href='https://github.com/pineapple-bois/Double_Pendulum_App',
                    target='_blank')
            ], style={'flex': '0 1 auto', 'alignSelf': 'center'}),
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'height': '100px'}),

        # Container for description of system
        html.Div([
            html.Div([
                dcc.Markdown('''
                ### The below figure shows a simple pendulum $OP_1$ suspended from another simple pendulum $P_{1}P_{2}$ by a frictionless hinge.
                ''', mathjax=True),
            ], style={'text-align': 'center', 'margin-top': '20px'}),  # Center-align the content and add margin,
            html.Div([
                dcc.Markdown('''
                `Simple` model: Rigid, massless, and inextensible rods are connected to point masses; $m_1$ & $m_2$.
                
                `Compound` model: The rods are modeled as [uniform thin rods](https://phys.libretexts.org/Courses/Joliet_Junior_College/Physics_201_-_Fall_2019v2/Book%3A_Custom_Physics_textbook_for_JJC/11%3A_Rotational_Kinematics_Angular_Momentum_and_Energy/11.06%3A_Calculating_Moments_of_Inertia) of evenly distributed masses; $M_1$ & $M_2$.
                ''', mathjax=True),
            ], style={'text-align': 'left', 'margin': '0 auto', 'max-width': '900px'}),
            html.Div([
                dcc.Markdown('''
                Both pendulums move in the $(x,y)$-plane. The system has two degrees of freedom, uniquely determined by the values of $\\theta_1$ & $\\theta_2$.
                ''', mathjax=True),
            ], style={'text-align': 'center', 'margin-top': '20px'}),  # Center-align the content and add margin,
        ]),

        # Container to establish a flexbox layout with two columns, instructions and image
        html.Div([
            # Column for instructions (Markdown)
            html.Div([
                dcc.Markdown('''
                ## Instructions

                - Please experiment with different initial conditions. The initial angles; $\\theta_1$ & $\\theta_2$ are measured counterclockwise in degrees. 
                  
                   
                - A negative angle gives clockwise rotation.
                
                
                - The angular velocities; $\omega_1$ & $\omega_2$ can be specified in degrees per second. *Interesting dynamics can be discovered simply releasing the pendulums from rest;* $(\\omega_i=0)$.  
                    
                    
                - `Unity Parameters` sets pendulum arms to $1 \\text{m}$ & masses to $1 \\text{kg}$, with $g = 9.81\\text{m s}^{-2}$.
                
                
                - Ensure all initial conditions and parameters are filled.
                
                
                - The default time interval is 20 seconds. The maximum is 120 seconds. 
                
                
                - `Acceleration due to gravity, m/s²` offers a dropdown to simulate the pendulum's behavior on [celestial bodies in our Solar System](https://nssdc.gsfc.nasa.gov/planetary/factsheet/planet_table_ratio.html). This parameter significantly affects the pendulum's motion, as gravity is the restoring force that influences the oscillation period and stability.
                
                
                Use the `Run Simulation` button to start the simulation.
                
                [Quantifying Chaotic Dynamics](\chaos) (Opens new page)
                ''', mathjax=True)
            ], style={'flex': '1', 'margin': '20px', 'font-size': "14px"}, className='instructions-column'),

            # Column for image
            html.Div([
                html.Img(src='assets/Images/Models_Joint_White.png', style={'max-width': '100%', 'height': 'auto'})
            ], style={'flex': '1'}, className='image-column'),
        ], style={'display': 'flex'}, className='instructions-image-container'),

        # Container for inputs and buttons
        html.Div(className='container', children=[
            # Column for model and buttons
            html.Div(className='column', children=[
                html.Div(className='input-group', children=[
                    html.Label('Model Type:', className='label'),
                    dcc.Dropdown(
                        id='model-type',
                        options=[
                            {'label': 'Simple', 'value': 'simple'},
                            {'label': 'Compound', 'value': 'compound'}
                        ],
                        value='simple',
                        clearable=False
                    ),
                ]),
                html.Div(className='input-group', children=[
                    html.Label('System Type:', className='label'),
                    dcc.Dropdown(
                        id='system-type',
                        options=[
                            {'label': 'Lagrangian', 'value': 'lagrangian'},
                            {'label': 'Hamiltonian', 'value': 'hamiltonian'}
                        ],
                        value='lagrangian',
                        clearable=False
                    ),
                ]),
                html.Div(className='container-buttons', children=[
                    html.Button('Reset', id='reset-button', n_clicks=0, className='button'),
                    html.Button('Run Simulation', id='submit-val', n_clicks=0, className='button'),
                ]),
            ]),
            # Column for initial conditions and time vector input
            html.Div(className='column', children=[
                html.Div(className='input-group', children=[
                    html.Label('Initial Conditions (θ1, θ2, ω1, ω2): degrees', className='label'),
                    dcc.Input(id='init_cond_theta1', type='number', placeholder='Angle 1', className='input'),
                    dcc.Input(id='init_cond_theta2', type='number', placeholder='Angle 2', className='input'),
                    dcc.Input(id='init_cond_omega1', type='number', placeholder='Angular velocity 1',
                              className='input'),
                    dcc.Input(id='init_cond_omega2', type='number', placeholder='Angular velocity 2',
                              className='input'),
                ]),
                html.Div(className='input-group', children=[
                    html.Label('Time Vector (start, stop): seconds', className='label'),
                    dcc.Input(id='time_start', type='number', placeholder='Start Time', value=0, className='input'),
                    dcc.Input(id='time_end', type='number', placeholder='End Time', value=20, className='input'),
                ]),
            ]),
            # Column for Parameters
            html.Div(className='column', children=[
                html.Div(className='container-buttons', children=[
                    html.Button('Set Unity Parameters', id='unity-parameters', n_clicks=0, className='button'),
                ]),
                html.Div(className='input-group', children=[
                    html.Label('Parameters (l1, l2, m1, m2, M1, M2, g)',
                               id='parameters-label', className='label'),
                    dcc.Input(id='param_l1', type='number', placeholder='l1 (length of rod 1)', className='input'),
                    dcc.Input(id='param_l2', type='number', placeholder='l2 (length of rod 2)', className='input'),
                    dcc.Input(id='param_m1', type='number', placeholder='m1 (mass of bob 1)',
                              className='input', style={'display': 'block'}),
                    dcc.Input(id='param_m2', type='number', placeholder='m2 (mass of bob 2)',
                              className='input', style={'display': 'block'}),
                    # M1, M2 initially hidden as simple is the default model
                    dcc.Input(id='param_M1', type='number', placeholder='M1 (mass of rod 1)',
                              className='input', style={'display': 'none'}),
                    dcc.Input(id='param_M2', type='number', placeholder='M2 (mass of rod 2)',
                              className='input', style={'display': 'none'}),
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
                        placeholder='Acceleration due to gravity, m/s²',  # Placeholder text
                        clearable=False,
                        searchable=False,)  # If you have a long list, you might want to make it searchable
                ]),
            ]),
        ]),

        # Loading spinner
        dcc.Loading(
            id="loading-1",
            type="default",  # or "circle", "dot", or "cube" for different spinner types
            children=[
                html.Div(id='animation-phase-container', className='above-graph-container', style={'display': 'none'},
                         children=[
                             dcc.Graph(id='pendulum-animation',
                                       config=config),
                             dcc.Graph(id='phase-graph',
                                       config=config),
                         ]),
                html.Div(id='time-graph-container', className='graph-container', style={'display': 'none'}, children=[
                    dcc.Graph(id='time-graph', responsive=True),
                ]),
            ],
            # Position the spinner at the top of the container
            style={'height': '100%', 'position': 'relative'}
        ),

        # Error message
        html.Div(id='error-message', style={
            'color': 'red',
            'textAlign': 'center',
            'margin': '20px',
            'font-size': "20px"
        }),

        html.Div(id='math-button-container', className='container-buttons', style={'display': 'none'}, children=[
            html.Button('Show Mathematics', id='show-maths', n_clicks=0, className='button-show'),
        ]),

        # Container for the "The Mathematics" section, initially hidden
        html.Div(id='mathematics-section', style={'display': 'none',
                                                  'margin-top': '20px',
                                                  'max-height': 'calc(100vh - 200px)'},
                 children=[
                     html.Div(id='math-content',
                     className='markdown-latex-container', style={'flex': 1}),
                 ]),
    ])
