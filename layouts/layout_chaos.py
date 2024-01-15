# Chaos page layout
from dash import html
from dash import dcc

# Derivation blurb
with open('assets/mathematics_section.txt', 'r') as file:
    math_section = file.read()


def get_chaos_layout():
    # This function returns the layout of the main page
    return html.Div([
        # Flex container for the title, chaos page link, and GitHub logo
        html.Div([
            # Link to the home page with text on two lines, allow it to shrink on small screens
            html.Div([
                html.A(["Home Page"],
                       className="title-link",
                       href="/home",
                       style={'fontSize': '20px', 'padding': '10px'}),
            ], style={'flex': '0 1 auto', 'alignSelf': 'center'}),

            # Title, which should stay centered with auto margins
            html.Div([
                html.H1([
                    html.Div("Quantifying Chaotic Dynamics:", style={'white-space': 'nowrap'})
                ], style={'textAlign': 'center', 'color': 'black', 'margin': 'auto'})
            ], style={'flex': '1 0 auto', 'minWidth': '0', 'textAlign': 'center'}),
            # minWidth: 0 ensures shrinkage if necessary

            # GitHub logo as a link, allow it to shrink on small screens
            html.Div([
                html.A([
                    html.Img(src='assets/github-mark.png', style={'height': '50px', 'width': '50px'})
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
                `Simple` model: Rigid, massless, and inextensible rods are connected to bobs; $m_1$ and $m_2$.

                `Compound` model: The rods are modeled as 'uniform thin rods' with evenly distributed masses; $M_1$ and $M_2$.
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
                ## Chaotic Dynamics
                
                The aim of this section is to compare 2 or 3 pendulums side by side with different initial conditions.
                
                ### Instructions
                
                - `Pendulums to compare`: Choose either two or three (default is two)

                - `Unity Parameters` sets pendulum arms to $1 \\text{m}$ & masses to $1 \\text{kg}$, with $g = 9.81\\text{m s}^{-2}$.

                - Ensure all initial conditions and parameters are filled.

                - The default time interval is 20 seconds. The maximum is 120 seconds. 

                [Return to Simulation](\home) (Opens new page)
                ''', mathjax=True)
            ], style={'flex': '1', 'margin': '20px', 'font-size': "14px"}, className='instructions-column'),

            # Column for image
            html.Div([
                html.Img(src='assets/Double_Pendulum.png', style={'max-width': '100%', 'height': 'auto'})
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
                    html.Label('Pendulums to compare:', className='label'),
                    dcc.Dropdown(
                        id='side-by-sides',
                        options=[
                            {'label': 'Two', 'value': 'two_pendulums'},
                            {'label': 'Three', 'value': 'three_pendulums'}
                        ],
                        placeholder='Select number of pendulums',
                        clearable=False
                    ),
                ]),
                html.Div(className='container-buttons', children=[
                    html.Button('Reset', id='reset-button', n_clicks=0, className='button'),
                ]),
            ]),

            # Time vector, reset & simulation
            html.Div(className='column', children=[
                html.Div(className='input-group', children=[
                    html.Label('Time Vector (start, stop): seconds', className='label'),
                    dcc.Input(id='time_start', type='number', placeholder='Start Time', value=0, className='input'),
                    dcc.Input(id='time_end', type='number', placeholder='End Time', value=20, className='input'),
                ]),
                html.Div(className='container-buttons', children=[
                    html.Button('Unity Parameters', id='unity-parameters', n_clicks=0, className='button'),
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
        # Hidden container for initial conditions and the 'run simulation' button
        html.Div(className='container', children=[
            html.Div(id='input-column-one', style={'display': 'none'}, children=[
                html.Div(className='input-group', children=[
                    html.Label('Pendulum A: (θ1, θ2, ω1, ω2): degrees', className='label'),
                    dcc.Input(id='pend_one_theta1', type='number', placeholder='Angle 1', className='input'),
                    dcc.Input(id='pend_one_theta2', type='number', placeholder='Angle 2', className='input'),
                    dcc.Input(id='pend_one_omega1', type='number', placeholder='Angular velocity 1', className='input'),
                    dcc.Input(id='pend_one_omega2', type='number', placeholder='Angular velocity 2', className='input'),
                ]),
            ]),
            html.Div(id='input-column-two', style={'display': 'none'}, children=[
                html.Div(className='input-group', children=[
                    html.Label('Pendulum B: (θ1, θ2, ω1, ω2): degrees', className='label'),
                    dcc.Input(id='pend_two_theta1', type='number', placeholder='Angle 1', className='input'),
                    dcc.Input(id='pend_two_theta2', type='number', placeholder='Angle 2', className='input'),
                    dcc.Input(id='pend_two_omega1', type='number', placeholder='Angular velocity 1', className='input'),
                    dcc.Input(id='pend_two_omega2', type='number', placeholder='Angular velocity 2', className='input'),
                ]),
            ]),
            html.Div(id='input-column-three', style={'display': 'none'}, children=[
                html.Div(className='input-group', children=[
                    html.Label('Pendulum C: (θ1, θ2, ω1, ω2): degrees', className='label'),
                    dcc.Input(id='pend_three_theta1', type='number', placeholder='Angle 1', className='input'),
                    dcc.Input(id='pend_three_theta2', type='number', placeholder='Angle 2', className='input'),
                    dcc.Input(id='pend_three_omega1', type='number', placeholder='Angular velocity 1',
                              className='input'),
                    dcc.Input(id='pend_three_omega2', type='number', placeholder='Angular velocity 2',
                              className='input'),
                ]),
            ]),
        ]),
        html.Div(className='container', children=[
            html.Div(id='run-simulation-button', style={'display': 'none'}, children=[
                # Run Simulation button
                html.Div(className='container-buttons', style={'display': 'block'}, children=[
                    html.Button('Run Simulation', id='submit-val', n_clicks=0, className='button'),
                ]),
            ]),
        ]),
        # Loading spinner
        dcc.Loading(
            id="loading-1",
            type="default",  # or "circle", "dot", or "cube" for different spinner types
            children=[  # new ID for multi pendulums
                # Container for animations with headers
                html.Div(id='animation-container', className='multi-graph-container', children=[
                    html.Div([
                        html.H4("Pendulum A"),
                        dcc.Graph(id='pendulum-a-animation'),
                        dcc.Graph(id='pendulum-a-phase')
                    ]),
                    html.Div([
                        html.H4("Pendulum B"),
                        dcc.Graph(id='pendulum-b-animation'),
                        dcc.Graph(id='pendulum-b-phase')
                    ]),
                    html.Div([
                        html.H4("Pendulum C"),
                        dcc.Graph(id='pendulum-c-animation'),
                        dcc.Graph(id='pendulum-c-phase')
                    ]),
                    # Add more graphs above as needed
                ], style={'display': 'grid'})
            ],
            # Position the spinner at the top of the container
            style={'height': '100%', 'position': 'relative'}
        ),
        # Error message
        html.Div(id='error-message-chaos', style={
            'color': 'red',
            'textAlign': 'center',
            'margin': '20px',
            'font-size': "20px"
        }),

        html.Div(id='math-button-container-chaos', className='container-buttons', style={'display': 'none'}, children=[
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