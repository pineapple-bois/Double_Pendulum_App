import plotly.graph_objs as go

# Define Matplotlib layout for plotly figures
mpl_layout = go.Layout(
    title_font=dict(family='Courier New, monospace', size=16, color='black'),
    paper_bgcolor='white',
    plot_bgcolor='white',
    xaxis=dict(
        titlefont=dict(family='Courier New, monospace', size=14, color='black'),
        showgrid=True,
        gridcolor='lightgrey'
    ),
    yaxis=dict(
        titlefont=dict(family='Courier New, monospace', size=14, color='black'),
        showgrid=True,
        gridcolor='lightgrey'
    )
)