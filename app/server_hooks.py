from flask import redirect, request

from app import config


def configure_server(server) -> None:
    """Attach optional deployment hooks to the Flask server."""
    if not config.FORCE_HTTPS:
        return

    @server.before_request
    def force_https_redirect():
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
        forwarded_scheme = forwarded_proto.split(",", 1)[0].strip().lower()

        if forwarded_scheme == "https" or request.is_secure:
            return None

        https_url = request.url.replace("http://", "https://", 1)
        return redirect(https_url, code=301)
