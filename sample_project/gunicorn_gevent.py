"""gunicorn + gevent config for the ``sample_project_gevent_ssr`` E2E target.

Mirrors a production gevent deployment: gunicorn's gevent worker monkey-patches
the stdlib, so a render call waiting on the SSR service yields to other
requests instead of blocking the worker. Gunicorn's own ``timeout`` is
worker-scoped (it would kill every in-flight request), so each request also
gets its own ``gevent.Timeout`` deadline raising an ``Exception`` subclass —
the shape that lets Django middleware turn it into an error page, and the one
the library's SSR fallback must not swallow.
"""

import os

bind = "0.0.0.0:8000"
workers = 1
worker_class = "gevent"
timeout = 120
accesslog = "-"
errorlog = "-"

REQUEST_DEADLINE_SECONDS = float(os.getenv("REQUEST_DEADLINE_SECONDS", "20"))
# Test-only: lets a spec shorten one request's deadline via a header, so it can
# make the deadline fire while the render call is still waiting.
E2E_TEST_HOOKS = os.getenv("E2E_TEST_HOOKS", "False").lower() == "true"
DEADLINE_HEADER = "X-E2E-REQUEST-DEADLINE"  # gunicorn upper-cases header names


class RequestDeadlineExceededError(Exception):
    pass


def _deadline_seconds(req) -> float:
    if E2E_TEST_HOOKS:
        for name, value in req.headers:
            if name == DEADLINE_HEADER:
                return float(value)
    return REQUEST_DEADLINE_SECONDS


def pre_request(worker, req):
    from gevent import Timeout

    req.deadline = Timeout(
        _deadline_seconds(req), exception=RequestDeadlineExceededError
    )
    req.deadline.start()


def post_request(worker, req, environ, resp):
    deadline = getattr(req, "deadline", None)
    if deadline is not None:
        deadline.cancel()
        deadline.close()
