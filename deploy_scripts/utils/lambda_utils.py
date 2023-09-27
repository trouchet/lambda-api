from .ecr_utils import build_ecr_url
from .misc import timing
from .default_values import LAMBDA_SLEEP_SECONDS, LAMBDA_UPDATE_TIME_OUT_SECONDS


def get_lambda_arn(g_client, function_name_):
    response = g_client.get_function(FunctionName=function_name_)
    return response["Configuration"]["FunctionArn"]


def build_lambda_uri(region_, lambda_arn_):
    uri_host = f"arn:aws:apigateway:{region_}:lambda:path"
    uri_route = f"2015-03-31/functions/{lambda_arn_}/invocations"
    return f"{uri_host}/{uri_route}"


def get_lambda_function_name(ecr_image_name: str):
    return f"lambda-fn-{ecr_image_name}"


def create_lambda_function(
        l_client,
        function_name,
        func_description,
        routed_url,
        role_arn):
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


def get_lambda_function(l_client, function_name):
    failure_message = f"Lambda function {function_name} does not exist"

    try:
        return l_client.get_function(FunctionName=function_name)

    except l_client.exceptions.ResourceNotFoundException:
        print(failure_message)

# snippet-start:[python.example_code.lambda.DeleteFunction]


def delete_lambda_function(l_client, function_name):
    """
    Deletes a Lambda function.

    :param function_name: The name of the function to delete.
    """
    try:
        return l_client.delete_function(FunctionName=function_name)
    except l_client.exceptions.ClientError:
        print(f"Couldn't delete function {function_name}.", )


def wait_for_lambda_deployment(lambda_client, lambda_function_name):
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

    print(
        f"Lambda function deployment duration: {deployment_duration:.2f} seconds")


@timing("Lambda Function deployment")
def deploy_lambda_function(
    lambda_client,
    func_description,
    aws_account_id,
    aws_region,
    ecr_image_name,
    role_arn
):
    # Function name (not public facing)
    lambda_function_name = get_lambda_function_name(ecr_image_name)

    # Retrieve (if already exists) or create a new Lambda function
    routed_url = build_ecr_url(aws_account_id, aws_region, ecr_image_name)

    create_lambda_function(
        lambda_client,
        lambda_function_name,
        func_description,
        routed_url,
        role_arn
    )

    wait_for_lambda_deployment(lambda_client, lambda_function_name)
