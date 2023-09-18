from json import load, JSONDecodeError 
from .default_values import DEFAULT_DELIMITER, DEFAULT_MULTIPLIER

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
    trust_policy_file_path = trust_policy_folder+"/"+"trust_policy.json"
    
    return load_JSON(trust_policy_file_path)

def get_lambda_usage_constraints(usage_constraints_folder):
    ## Rate limits: Harsh since this will be public facing
    ## Quota: Low daily limits for the same reason
    usage_file_path = usage_constraints_folder+"/"+"api_usage_constraints.json"
    return load_JSON(usage_file_path)

def repeat_delimiter(multiplier: int, delimiter: str):
    return multiplier * delimiter

def fence(multiplier: int = DEFAULT_MULTIPLIER, delimiter: str = DEFAULT_DELIMITER) -> str:
    return repeat_delimiter(multiplier, delimiter)

def get_start_message(task_name: str):
    return f"Task \"{task_name}\" just started!"

def get_success_message(task_name: str) -> str:
    return f"Task \"{task_name}\" finished successfully!"

def print_start_message(task_name: str):
    fence_string=fence()
    
    print(fence_string)
    start_msg=get_start_message(task_name)
    print(start_msg)
    print(fence_string)

def print_success_message(task_name: str):
    fence_string=fence()
    
    print(fence_string)
    success_msg=get_success_message(task_name)
    print(success_msg)
    print(fence_string)
    
    print()