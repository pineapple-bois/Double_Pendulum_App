import plotly.graph_objs as go


INTERACTIVE_TEXTBOOK_FONT = (
    '"Helvetica Neue", Helvetica, Arial, system-ui, -apple-system, '
    'BlinkMacSystemFont, "Segoe UI", sans-serif'
)

PLOT_THEME = {
    "surface": "#ffffff",
    "text": "#1f2933",
    "muted": "#5f6b6b",
    "accent": "#00635d",
    "accent_dark": "#004c47",
    "series_secondary": "#5f6b6b",
    "grid": "#ddd8d0",
    "axis": "#82908e",
}


def _axis_style():
    return dict(
        title=dict(
            font=dict(
                family=INTERACTIVE_TEXTBOOK_FONT,
                size=14,
                color=PLOT_THEME["text"],
            )
        ),
        tickfont=dict(
            family=INTERACTIVE_TEXTBOOK_FONT,
            size=12,
            color=PLOT_THEME["muted"],
        ),
        showgrid=True,
        gridcolor=PLOT_THEME["grid"],
        gridwidth=1,
        showline=True,
        linecolor=PLOT_THEME["axis"],
        zerolinecolor=PLOT_THEME["axis"],
        fixedrange=True,
    )


mpl_layout = go.Layout(
    paper_bgcolor=PLOT_THEME["surface"],
    plot_bgcolor=PLOT_THEME["surface"],
    font=dict(
        family=INTERACTIVE_TEXTBOOK_FONT,
        size=14,
        color=PLOT_THEME["text"],
    ),
    colorway=[
        PLOT_THEME["accent"],
        PLOT_THEME["series_secondary"],
        PLOT_THEME["accent_dark"],
    ],
    xaxis=_axis_style(),
    yaxis=_axis_style(),
    hoverlabel=dict(
        bgcolor=PLOT_THEME["surface"],
        bordercolor=PLOT_THEME["grid"],
        font=dict(
            family=INTERACTIVE_TEXTBOOK_FONT,
            color=PLOT_THEME["text"],
        ),
    ),
    modebar=dict(
        bgcolor="rgba(255,255,255,0.9)",
        color=PLOT_THEME["muted"],
        activecolor=PLOT_THEME["accent"],
    ),
    dragmode=False,
    showlegend=False,
)
