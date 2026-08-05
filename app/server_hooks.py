from flask import Response, abort, redirect, request

from app import config
from app.content.routes import PUBLIC_ROUTE_ITEMS


DASH_CATCH_ALL_RULE = "/<path:path>"
PUBLIC_ROUTE_PATHS = frozenset(page.path for page in PUBLIC_ROUTE_ITEMS)
ROBOTS_TXT = """User-agent: AhrefsBot
Disallow: /

User-agent: *
Allow: /
"""


def configure_server(server) -> None:
    """Attach routing, response-security, and optional deployment hooks."""

    @server.get("/robots.txt")
    def robots_txt():
        return Response(ROBOTS_TXT, mimetype="text/plain")

    if config.FORCE_HTTPS:
        @server.before_request
        def force_https_redirect():
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
            forwarded_scheme = forwarded_proto.split(",", 1)[0].strip().lower()

            if forwarded_scheme == "https" or request.is_secure:
                return None

            https_url = request.url.replace("http://", "https://", 1)
            return redirect(https_url, code=301)

    @server.before_request
    def reject_unknown_dash_routes():
        matched_rule = request.url_rule
        if (
            matched_rule is not None
            and matched_rule.rule == DASH_CATCH_ALL_RULE
            and request.path not in PUBLIC_ROUTE_PATHS
        ):
            abort(404)
        return None

    @server.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault(
            "Referrer-Policy",
            "strict-origin-when-cross-origin",
        )
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        return response
