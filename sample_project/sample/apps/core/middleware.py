from inertia import share


class ShareDemoMiddleware:
    """Cross-cutting props injected on every Inertia response via `share()`."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        share(
            request,
            app_name="Inertia Django Sample",
            user=lambda: {
                "name": "Brandon",
                "role": "goalie",
            },
        )
        return self.get_response(request)
