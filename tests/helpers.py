def extract_dash_text(component):
    """Return all string children from a Dash component tree."""
    messages = []

    def collect_strings(node):
        if node is None:
            return
        if isinstance(node, str):
            messages.append(node)
            return
        if isinstance(node, (list, tuple)):
            for child in node:
                collect_strings(child)
            return
        if hasattr(node, "children"):
            collect_strings(node.children)

    collect_strings(component)
    return messages
