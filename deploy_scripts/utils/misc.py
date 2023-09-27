from json import load, JSONDecodeError


def load_JSON(json_file_path_):
    try:
        # Load the JSON data from the file
        with open(json_file_path_, "r") as json_file:
            json_file_content = load(json_file)

        # Print the loaded trust_policy dictionary
        print("Loaded JSON:")
        print(json_file_content)

        return json_file_content

    except FileNotFoundError:
        print(f"JSON file not found at path: {json_file_path_}")
    except JSONDecodeError as e:
        print(f"Error loading JSON: {e}")


def get_trust_policy(trust_policy_folder):
    trust_policy_file_path = trust_policy_folder + "/" + "trust_policy.json"

    return load_JSON(trust_policy_file_path)


def get_lambda_usage_constraints(usage_constraints_folder):
    # Rate limits: Harsh since this will be public facing
    # Quota: Low daily limits for the same reason
    usage_file_path = usage_constraints_folder + "/" + "api_usage_constraints.json"
    return load_JSON(usage_file_path)


def timing(custom_message):
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
