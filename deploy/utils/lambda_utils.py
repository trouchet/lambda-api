from .misc import handle_aws_errors
from .default_values import LAMBDA_SLEEP_SECONDS, LAMBDA_UPDATE_TIME_OUT_SECONDS

def build_lambda_uri(region_, lambda_arn_):
    """
    Build a Lambda URI using the Lambda ARN.

    Parameters:
    region_ (str): The AWS region.
    lambda_arn_ (str): The ARN of the Lambda function.

    Returns:
    str: The Lambda URI.
    """

    uri_host = f"arn:aws:apigateway:{region_}:lambda:path"
    uri_route = f"2015-03-31/functions/{lambda_arn_}/invocations"
    return f"{uri_host}/{uri_route}"


def get_lambda_function_name(ecr_image_name: str):
    """
    Generate a Lambda function name based on an ECR image name.

    Parameters:
    ecr_image_name (str): The name of the ECR image.

    Returns:
    str: The generated Lambda function name.
    """

    return f"lambda-fn-{ecr_image_name}"

@handle_aws_errors
def get_lambda_arn(g_client, function_name_):
    """
    Get the ARN (Amazon Resource Name) of a Lambda function.

    Parameters:
    g_client (boto3.client): AWS Lambda client.
    function_name_ (str): The name of the Lambda function.

    Returns:
    str: The ARN of the Lambda function.
    """

    response = g_client.get_function(FunctionName=function_name_)
    return response["Configuration"]["FunctionArn"]

@handle_aws_errors
def create_lambda_function(
        l_client,
        function_name,
        func_description,
        routed_url,
        role_arn):
    """
    Create a Lambda function.

    Parameters:
    l_client (boto3.client): AWS Lambda client.
    function_name (str): The name of the Lambda function.
    func_description (str): The description of the Lambda function.
    routed_url (str): The routed URL for the Lambda function.
    role_arn (str): The ARN of the IAM role associated with the Lambda function.

    Returns:
    dict: The created Lambda function details.
    """
    
    failure_message = f"Lambda function {function_name} already exists"

    code_payload = {"ImageUri": routed_url}

    try:
        return l_client.create_function(
            FunctionName=function_name,
            Role=role_arn,
            PackageType="Image",
            Code=code_payload,
            Description=func_description,
            Timeout=10,
            MemorySize=256,
            Publish=True,
        )

    except l_client.exceptions.ResourceNotFoundException:
        print(failure_message)


@handle_aws_errors
def get_lambda_function(l_client, function_name):
    """
    Get details of a Lambda function.

    Parameters:
    l_client (boto3.client): AWS Lambda client.
    function_name (str): The name of the Lambda function.

    Returns:
    dict: The details of the Lambda function.
    """

    failure_message = f"Lambda function {function_name} does not exist"

    try:
        return l_client.get_function(FunctionName=function_name)

    except l_client.exceptions.ResourceNotFoundException:
        print(failure_message)


def delete_lambda_function(l_client, function_name):
    """
    Deletes a Lambda function.

    :param function_name: The name of the function to delete.
    """
    try:
        return l_client.delete_function(FunctionName=function_name)
    except l_client.exceptions.ClientError:
        print(f"Couldn't delete function {function_name}.", )


@handle_aws_errors
def wait_for_lambda_deployment(lambda_client, lambda_function_name):
    """
    Wait for the deployment of a Lambda function.

    Parameters:
    lambda_client (boto3.client): AWS Lambda client.
    lambda_function_name (str): The name of the Lambda function.
    """

    from time import time, sleep

    start_time = time()

    response_get = get_lambda_function(lambda_client, lambda_function_name)

    def is_creation_pending(response):
        return response["Configuration"]["State"] == "Pending"

    while is_creation_pending(response_get):
        try:
            response_get = get_lambda_function(
                lambda_client, lambda_function_name)
        except ValueError as msg:
            print(str(msg))

        current_time = time()
        deployment_duration = current_time - start_time

        if deployment_duration > LAMBDA_UPDATE_TIME_OUT_SECONDS:
            raise TimeoutError("Lambda deployment timed out")

        print("Lambda deployment is still in progress. Waiting...")

        # Wait before checking again
        sleep(LAMBDA_SLEEP_SECONDS)

    duration_seconds=f"{deployment_duration:.2f} seconds"
    lambda_deploy_message=f"Lambda function deployment duration: {duration_seconds}"
    print(lambda_deploy_message)

def deploy_lambda_function(
    lambda_client, lambda_function_name, lambda_function_description,
    routed_ecr_url, role_arn
):
    """
    Deploy a Lambda function.

    Parameters:
    lambda_client (boto3.client): AWS Lambda client.
    func_description (str): The description of the Lambda function.
    aws_account_id (str): The AWS account ID.
    aws_region (str): The AWS region.
    routed_ecr_url (str): The uri of the ECR image.
    role_arn (str): The ARN of the IAM role associated with the Lambda function.
    """
    print(f'Creating Lambda Function {lambda_function_name}...')
    
    # Retrieve (if already exists) or create a new Lambda function
    create_lambda_function(
        lambda_client, lambda_function_name, lambda_function_description, \
        routed_ecr_url, role_arn
    )

    wait_for_lambda_deployment(lambda_client, lambda_function_name)


def lambda_exists(lambda_client, lambda_function_name):
    """
    Check if a Lambda function with the given name exists.

    Parameters:
    - lambda_client (boto3.client): AWS Lambda client.
    - lambda_function_name (str): The name of the Lambda function.

    Returns:
    bool: True if the Lambda function exists, False otherwise.
    """
    try:
        lambda_client.get_function(FunctionName=lambda_function_name)
        return True
    except lambda_client.exceptions.ResourceNotFoundException:
        return False


def update_lambda_function_code(
    lambda_client, lambda_function_name, routed_ecr_url
):
    """
    Update the Lambda function code with a new ECR image.

    Parameters:
    - lambda_client (boto3.client): AWS Lambda client.
    - lambda_function_name (str): The name of the Lambda function.
    - routed_ecr_url (str): The uri of the ECR repository.

    Returns:
    tuple: A tuple containing the Lambda function name and URI.
    """
    print(f'Updating Lambda Function {lambda_function_name}...')
    
    # Update the Lambda function code
    lambda_client.update_function_code(
        FunctionName=lambda_function_name,
        ImageUri=routed_ecr_url
    )


def update_or_deploy_lambda_function(\
        lambda_client, \
        lambda_function_name, \
        lambda_function_description, \
        ecr_image_url, role_arn
    ):
    """
    Update or deploy a Lambda function based on whether it already exists.

    This function checks if a Lambda function with the specified name already exists.
    If it exists, it updates the Lambda function code with the provided ECR image URL.
    If it doesn't exist, it deploys a new Lambda function with the ECR image.

    Parameters:
    - lambda_client (boto3.client): AWS Lambda client.
    - lambda_function_name (str): The name of the Lambda function.
    - lambda_function_description (str): The description of the Lambda function.
    - ecr_image_url (str): The URL of the ECR image.
    - role_arn (str): The ARN of the IAM role associated with the Lambda function.

    Returns:
    tuple: A tuple containing the Lambda function name and URI.
    """

    if lambda_exists(lambda_client, lambda_function_name):
        # Update the Lambda function code
        update_lambda_function_code(lambda_client, lambda_function_name, ecr_image_url)
    else:
        # Deploy a new Lambda function with the ECR image
        deploy_lambda_function(
            lambda_client, lambda_function_name, lambda_function_description, ecr_image_url, role_arn
        )
