"""
Module Docstring: Model Prediction Function

This module defines a function for making predictions using a pre-loaded model. 
The model can be loaded either locally or  from Amazon S3, providing flexibility 
in usage.

Functions:
- model_prediction_map(payload_list, model=None): This function takes a list of payloads as 
input and performs a custom transformation (square_lambda) on each payload element using 
the `map` function. The transformed results are returned as a list.

Usage:
1. Load the model locally:
    from cloudpickle import load
    with open('model.pickle', 'rb') as f:
        model = load(f)
    result = model_prediction_map(payload_list, model)

2. Load the model from Amazon S3:
    # Load model from S3 using an appropriate mechanism

Parameters:
- payload_list (list): A list of payloads to be processed.
- model (object): The pre-loaded machine learning model. 
If None, the function will expect you to provide a model when calling the function.


Author: brunolnetto@gmail.com
Date: 17 09 2023
"""

# Set the allowed payload types
ALLOWED_TYPES = (int, float)

def model_prediction_map(payload_list: list):
    """
    Maps a list of payloads to their squared values using a predefined square lambda function.

    Parameters:
    - payload_list (list): A list of payloads to be processed.

    Returns:
    - list: A list of squared values corresponding to the input payload list.
    """
    
    # REPLACE WITH: ####################################
    #   - command call model.predict(payload).tolist()
    def square_lambda(x):
        return x ** 2
    
    square_map = map(square_lambda, payload_list)
    ####################################################

    return list(square_map)
