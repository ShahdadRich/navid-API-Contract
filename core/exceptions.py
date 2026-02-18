from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    if response is not None:
        # Custom format for errors
        custom_data = {
            "message": "",
            "code": "",
            "details": response.data
        }

        # Try to extract a useful message
        if isinstance(response.data, dict):
            if "detail" in response.data:
                custom_data["message"] = response.data["detail"]
                del response.data["detail"]
            elif "non_field_errors" in response.data:
                custom_data["message"] = response.data["non_field_errors"][0]
            else:
                custom_data["message"] = "Validation Error"
        elif isinstance(response.data, list):
            custom_data["message"] = response.data[0]

        # Set machine readable code
        if response.status_code == 429:
            custom_data["code"] = "RATE_LIMITED"
        elif response.status_code == 400:
            custom_data["code"] = "VALIDATION_ERROR"
        elif hasattr(exc, "get_codes"):
            codes = exc.get_codes()
            if isinstance(codes, dict):
                 # Just take the first code we find if it's a dict
                 first_key = next(iter(codes))
                 code = codes[first_key]
                 if isinstance(code, list):
                     code = code[0]
                 custom_data["code"] = str(code).upper()
            else:
                custom_data["code"] = str(codes).upper()
        else:
            # Fallback codes based on status
            status_code = response.status_code
            if status_code == 401:
                custom_data["code"] = "UNAUTHORIZED"
            elif status_code == 403:
                custom_data["code"] = "FORBIDDEN"
            elif status_code == 404:
                custom_data["code"] = "NOT_FOUND"
            elif status_code == 400:
                custom_data["code"] = "VALIDATION_ERROR"
            elif status_code == 429:
                custom_data["code"] = "RATE_LIMITED"
            else:
                custom_data["code"] = "ERROR"

        response.data = custom_data

    return response
