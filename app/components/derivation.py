from dash import dcc, html


def render_markdown(text, class_name="equation-markdown"):
    return dcc.Markdown(text, mathjax=True, className=class_name)


def render_model_summary(card):
    return html.Article(
        className="equations-model-card",
        children=[
            html.Div(
                className="equations-model-copy",
                children=[
                    html.H3(card.title, className="equations-model-title"),
                    render_markdown(card.summary, "equations-model-summary"),
                ],
            ),
            html.Div(
                className="equations-model-image-wrap",
                children=[
                    html.Img(src=card.image_src, className="equations-model-image", alt=card.title),
                ],
            ),
            html.Ul(
                className="equations-model-detail-list",
                children=[
                    html.Li(render_markdown(detail, "equations-model-detail"))
                    for detail in card.details
                ],
            ),
        ],
    )


def render_branch_card(card):
    return html.A(
        href=card.href,
        className="equations-branch-card",
        children=[
            html.H3(card.title, className="equations-branch-title"),
            html.P(card.summary, className="equations-branch-summary"),
            html.Ul(
                className="equations-branch-list",
                children=[
                    html.Li(render_markdown(point, "equations-branch-point"))
                    for point in card.points
                ],
            ),
        ],
    )


def render_equation_block(block):
    body = [
        render_markdown(block.markdown),
    ]
    if block.note:
        body.append(render_markdown(block.note, "equations-block-note"))

    if block.collapsed:
        return html.Details(
            className="equations-details-block",
            children=[
                html.Summary(block.title, className="equations-details-summary"),
                html.Div(className="equations-details-body", children=body),
            ],
        )

    return html.Article(
        className="equations-block",
        children=[
            html.H3(block.title, className="equations-block-title"),
            *body,
        ],
    )


def render_derivation_section(section):
    return html.Section(
        id=section.section_id,
        className="equations-section",
        children=[
            html.Div(
                className="equations-section-heading",
                children=[
                    html.P(section.eyebrow, className="equations-eyebrow"),
                    html.H2(section.title, className="equations-section-title"),
                    html.P(section.lead, className="equations-section-lead"),
                ],
            ),
            html.Div(
                className="equations-block-stack",
                children=[render_equation_block(block) for block in section.blocks],
            ),
        ],
    )
