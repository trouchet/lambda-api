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