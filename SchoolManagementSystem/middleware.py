import re

from django.apps import apps
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import NoReverseMatch, reverse


class AdminAddModalRedirectMiddleware:
    pattern = re.compile(r"^/admin/(?P<app_label>[^/]+)/(?P<model_name>[^/]+)/add/$")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "GET" and "_popup" not in request.GET and "_modal" not in request.GET:
            match = self.pattern.match(request.path_info)
            if match:
                app_label = match.group("app_label")
                model_name = match.group("model_name")
                try:
                    model = apps.get_model(app_label, model_name)
                except LookupError:
                    model = None
                if model is not None and model in admin.site._registry:
                    try:
                        changelist_url = reverse(f"admin:{app_label}_{model_name}_changelist")
                    except NoReverseMatch:
                        changelist_url = None
                    if changelist_url:
                        return HttpResponseRedirect(f"{changelist_url}?_open_admin_add=1")
        response = self.get_response(request)

        if request.GET.get("_modal") == "1":
            response.headers.pop("X-Frame-Options", None)
            csp = response.headers.get("Content-Security-Policy")
            if csp and "frame-ancestors" in csp:
                directives = [
                    directive.strip()
                    for directive in csp.split(";")
                    if directive.strip() and not directive.strip().startswith("frame-ancestors")
                ]
                if directives:
                    response.headers["Content-Security-Policy"] = "; ".join(directives)
                else:
                    response.headers.pop("Content-Security-Policy", None)

        return response
