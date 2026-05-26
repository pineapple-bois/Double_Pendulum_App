import plotly.graph_objs as go


mpl_layout = go.Layout(
    paper_bgcolor="white",
    plot_bgcolor="white",
    xaxis=dict(
        title=dict(font=dict(family="Red Hat Display, sans-serif", size=14, color="black")),
        showgrid=True,
        gridcolor="lightgrey",
        fixedrange=True,
    ),
    yaxis=dict(
        title=dict(font=dict(family="Red Hat Display, sans-serif", size=14, color="black")),
        showgrid=True,
        gridcolor="lightgrey",
        fixedrange=True,
    ),
    dragmode=False,
    showlegend=False,
)

