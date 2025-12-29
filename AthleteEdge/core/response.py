from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response as RestResponse


class Response(RestResponse):
    def __init__(
        self,
        data=None,
        message="",
        status=None,
        success=True,
        template_name=None,
        headers=None,
        exception=False,
        content_type=None,
    ):

        response_data = {
            "meta_data": {
                "success": success,
                "status_code": status,
                "message": message,
            },
            "data": data if data is not None else {},
        }

        if response_data["data"] == None:
            response_data.pop("data")

        super().__init__(
            response_data, status, template_name, headers, exception, content_type
        )


class Error(RestResponse):
    def __init__(
        self,
        data=None,
        message="",
        status=None,
        success=None,
        template_name=None,
        headers=None,
        exception=False,
        content_type=None,
    ):

        response_data = {
            "meta_data": {
                "success": False,
                "status_code": status,
                "message": message,
            },
            "data": data if data is not None else {},
        }

        super().__init__(
            response_data, status, template_name, headers, exception, content_type
        )


class UnauthorizedRequest(RestResponse):
    def __init__(self):

        response_data = {
            "meta_data": {
                "success": False,
                "status_code": 401,
                "message": "Unauthorized Request",
            },
            "data": {},
        }

        super().__init__(response_data, 401)


class InvalidOrExpiredTokenRequest(RestResponse):
    def __init__(self):

        response_data = {
            "meta_data": {
                "success": False,
                "status_code": 401,
                "message": "Invalid or expired access token",
            },
            "data": {},
        }

        super().__init__(response_data, 401)


class JSONRendererError:
    def __init__(self, ErrorClass):
        self.response = ErrorClass()
        self.response.accepted_renderer = JSONRenderer()
        self.response.accepted_media_type = "application/json"
        self.response.renderer_context = {}
        self.response.render()
