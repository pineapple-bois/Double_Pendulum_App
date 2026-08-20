from urllib.parse import unquote_plus

from flask import Response, make_response, redirect, request

from app import config
from app.content.routes import PUBLIC_ROUTE_ITEMS


DASH_CATCH_ALL_RULE = "/<path:path>"
PUBLIC_ROUTE_PATHS = frozenset(page.path for page in PUBLIC_ROUTE_ITEMS)
ROBOTS_TXT = """User-agent: AhrefsBot
Disallow: /

User-agent: *
Allow: /
"""
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=()"


def _plain_not_found():
    return Response("Not Found\n", status=404, mimetype="text/plain")


def _is_scanner_probe(path: str, query_string: bytes) -> bool:
    normalized = path.lower().rstrip("/") or "/"
    segments = tuple(segment for segment in normalized.split("/") if segment)
    query = unquote_plus(query_string.decode("utf-8", errors="replace")).lower()

    if any(segment.endswith(".php") for segment in segments):
        return True
    if any(
        segment in {"wp", "wordpress", "wp-includes"}
        or segment.startswith("wp-")
        for segment in segments
    ):
        return True
    if "rest_route=/wp/" in query:
        return True
    if any(
        segment in {".git", ".svn", ".hg"}
        or segment == ".env"
        or segment.startswith(".env.")
        for segment in segments
    ):
        return True
    return any(
        segment in {"composer.json", "package-lock.json"}
        for segment in segments
    )


def configure_server(server, *, dash_index_renderer=None) -> None:
    """Attach routing, response-security, and optional deployment hooks."""

    server.config["TRUSTED_HOSTS"] = (
        list(config.TRUSTED_HOSTS)
        if config.TRUSTED_HOSTS is not None
        else None
    )

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
    def handle_unknown_dash_routes():
        matched_rule = request.url_rule
        if (
            matched_rule is not None
            and matched_rule.rule == DASH_CATCH_ALL_RULE
            and request.path not in PUBLIC_ROUTE_PATHS
        ):
            final_segment = request.path.rsplit("/", 1)[-1]
            if (
                request.method not in {"GET", "HEAD"}
                or dash_index_renderer is None
                or _is_scanner_probe(request.path, request.query_string)
                or request.path.startswith("/api/")
                or "." in final_segment
            ):
                return _plain_not_found()

            response = make_response(dash_index_renderer(), 404)
            response.headers["Cache-Control"] = "no-store"
            return response
        return None

    @server.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault(
            "Referrer-Policy",
            "strict-origin-when-cross-origin",
        )
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        return response
