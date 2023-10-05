from json import load, JSONDecodeError
from botocore.exceptions import ClientError, BotoCoreError

def load_JSON(json_file_path_):
    """
    Load JSON data from a file.

    Parameters:
    json_file_path_ (str): The path to the JSON file to be loaded.

    Returns:
    dict: The loaded JSON data.

    Raises:
    FileNotFoundError: If the JSON file is not found.
    JSONDecodeError: If there is an error decoding the JSON data.
    """

    try:
        # Load the JSON data from the file
        with open(json_file_path_, "r") as json_file:
            json_file_content = load(json_file)

        # Print the loaded trust_policy dictionary
        print(f"Loaded JSON: {json_file_path_}")

        return json_file_content

    except FileNotFoundError:
        print(f"JSON file not found at path: {json_file_path_}")
    except JSONDecodeError as e:
        print(f"Error loading JSON: {e}")


def get_trust_policy(trust_policy_folder):
    """
    Get the trust policy from a specified folder.

    Parameters:
    trust_policy_folder (str): The folder containing the trust policy file.

    Returns:
    dict: The trust policy data.
    """

    trust_policy_file_path = trust_policy_folder + "/" + "trust_policy.json"

    return load_JSON(trust_policy_file_path)

def get_current_function_folder():
    from os import path
    from inspect import currentframe

    # Get the filename of the current frame (function or method)
    current_frame = currentframe()
    current_filename = current_frame.f_code.co_filename
    
    # Get the directory path of the current filename
    current_folder = path.dirname(path.abspath(current_filename))
    
    return current_folder

def get_lambda_usage_constraints(usage_constraints_folder):
    """
    Get lambda usage constraints from a specified folder.

    Parameters:
    usage_constraints_folder (str): The folder containing the usage constraints file.

    Returns:
    dict: The lambda usage constraints data.
    """

    # Rate limits: Harsh since this will be public facing
    # Quota: Low daily limits for the same reason
    usage_file_path = usage_constraints_folder + "/" + "api_usage_constraints.json"
    return load_JSON(usage_file_path)


def timing(custom_message):
    """
    A decorator function for measuring the execution time of a function.

    Parameters:
    custom_message (str): A custom message to describe the executed function.

    Returns:
    function: A decorator function.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            from time import time

            # Record the start time
            start_time = time()

            # Initial message
            print(f"Starting execution of {custom_message}...")

            # Call the wrapped function
            result = func(*args, **kwargs)

            # Calculate the time spent
            end_time = time()
            elapsed_time = end_time - start_time

            # Ending message
            print(f"Finished execution of {custom_message}.")
            print(f"Time taken: {elapsed_time:.2f} seconds")

            return result
        return wrapper
    return decorator

def get_calling_module_folder(calling_module_file):
    from os import path

    # Get the directory path of the calling module
    abs_path = path.abspath(calling_module_file)
    calling_module_folder = path.dirname(abs_path)
    return calling_module_folder

def handle_aws_errors(func):
    """
    A decorator for handling AWS SDK errors in wrapped functions.

    This decorator catches and handles AWS SDK errors, such as `botocore.exceptions.ClientError` and
    `botocore.exceptions.BotoCoreError`, providing a consistent error handling approach.

    Parameters:
    - func: The function to be wrapped.

    Returns:
    - The result of the wrapped function or None in case of errors.
    """
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except ClientError as e:
            print(f"An error occurred: {e}")
            return None, None
        except BotoCoreError as e:
            print(f"An AWS SDK error occurred: {e}")
            return None, None
    return wrapper