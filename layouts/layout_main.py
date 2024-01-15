# Main page layout
from dash import html
from dash import dcc

# Derivation blurb
with open('assets/mathematics_section.txt', 'r') as file:
    math_section = file.read()


def get_main_layout():
    # This function returns the layout of the main page
    return html.Div([
        # Flex container for the title and GitHub logo
        html.Div([
            # Title
            html.Div([
                html.H1("Double Pendulum Simulation: Lagrangian Formulation",
                        style={'text-align': 'center', 'color': 'black'})
            ], style={'flex': 1}),  # Title container taking up the full width

            # GitHub logo as a link
            html.A([
                html.Img(src='assets/github-mark.png',
                         style={'height': '50px', 'width': '50px'})
            ], href='https://github.com/pineapple-bois/Double_Pendulum_App',
                target='_blank',
                style={'align-self': 'center'}),
        ], style={'display': 'flex', 'justify-content': 'space-between', 'align-items': 'center'}),

        # Container to establish a flexbox layout with two columns, instructions and image
        html.Div([
            # Column for instructions (Markdown)
            html.Div([
                dcc.Markdown('''
                ## Instructions

                - Please experiment with different initial conditions. 
                - The initial angles; $\\theta_1$ & $\\theta_2$ are measured counterclockwise in degrees. 
                - A negative angle gives clockwise rotation.

                - The angular velocities; $\omega_1$ & $\omega_2$ can be specified in degrees per second
                    - *Interesting dynamics can be discovered simply releasing the pendulums from rest;* $(\\omega_i=0)$.  

                - `Unity Parameters` sets pendulum arms to $1 \\text{m}$ & masses to $1 \\text{kg}$, with $g = 9.81\\text{m s}^{-2}$.

                - Ensure all initial conditions and parameters are filled.

                - There are two models available: 
                    - `Simple` (the default) models a massless rod.
                    - `Compound` models a rod with uniform mass distribution along its length. 

                - The default time interval is 20 seconds. The maximum is 120 seconds. 

                - Use the `Run Simulation` button to start the simulation.

                ## [Explore Chaotic Dynamics](/chaos) (Opens a new page)
                ''', mathjax=True)
            ], style={'flex': 1, 'margin': '20px', 'font-size': "14px"}),

            # Column for image
            html.Div([
                html.Img(src='assets/Double_Pendulum.png', style={'max-width': '100%', 'height': 'auto'})
            ], style={'flex': 1}),  # Same flex value to take equal space as the instructions column
        ], style={'display': 'flex'}),  # This creates a flex container with row direction by default

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
                html.Div(className='container-buttons', children=[
                    html.Button('Unity Parameters', id='unity-parameters', n_clicks=0, className='button'),
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
                html.Div(className='input-group', children=[
                    html.Label('Parameters (l1, l2, m1, m2, M1, M2, g): m, kg, m/s',
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
                    dcc.Input(id='param_g', type='number', placeholder='g (acceleration due to gravity)',
                              className='input'),
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
                             dcc.Graph(id='pendulum-animation'),
                             dcc.Graph(id='phase-graph'),
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
                     html.Div([
                         dcc.Markdown(math_section, mathjax=True)
                     ], className='markdown-latex-container', style={'flex': 1}),
                 ]),
    ])
