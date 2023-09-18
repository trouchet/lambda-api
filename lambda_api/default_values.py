"""
Module Docstring: Constants for API Endpoint Handling

This module defines a set of constants for use in API endpoint handling. It includes default error messages and status codes for different scenarios encountered when processing API requests.

Constants:
- DEFAULT_TYPE_ERROR_MESSAGE: The default error message to be used when encountering an unknown prediction input format.
- SUCCESS_STATUS_CODE: The default HTTP status code (200) to be used for successful API responses.
- CLIENT_ERROR_STATUS_CODE: The default HTTP status code (400) to be used for client-related errors in API responses.
- SERVER_ERROR_STATUS_CODE: The default HTTP status code (500) to be used for server-related errors in API responses.

These constants can be imported and used in various parts of an API implementation to ensure consistency in error messages and status codes.

Usage:
    from endpoint_constants import DEFAULT_TYPE_ERROR_MESSAGE, SUCCESS_STATUS_CODE, CLIENT_ERROR_STATUS_CODE, SERVER_ERROR_STATUS_CODE

Author: brunolnetto@gmail.com
Date: 17 09 2023
"""

# Default error message for type of endpoint variable
DEFAULT_TYPE_ERROR_MESSAGE = "Unknown prediction input format."

# Default success status code
SUCCESS_STATUS_CODE = 200

# Default client error status code
CLIENT_ERROR_STATUS_CODE = 400

# Default server error status code
SERVER_ERROR_STATUS_CODE = 500
