from boto3 import client

from .utils.misc import get_lambda_usage_constraints, \
    get_trust_policy
from .utils.iam_utils import try_attach_role_policy
from .utils.ecr_utils import pipe_docker_image_to_ecr
from .utils.lambda_utils import get_lambda_function_name, \
    deploy_lambda_function, \
    delete_lambda_function, \
    get_lambda_arn, \
    build_lambda_uri
from .utils.api_gateway_utils import delete_apis_by_name, \
    deploy_rest_api, \
    add_apigateway_permission, \
    build_api_url
from .utils.misc import timing


def do_ecr_update(aws_account_id_, aws_region_, ecr_image_name_):
    """
    Perform the ECR update workflow, including creating and pushing a Docker image to AWS ECR.

    Parameters:
    - aws_account_id_ (str): AWS account ID.
    - aws_region_ (str): AWS region.
    - ecr_image_name_ (str): The name of the ECR repository.
    """

    # The id "role_arn" will be used on lambda deployment
    pipe_docker_image_to_ecr(aws_account_id_, aws_region_, ecr_image_name_)


def do_iam_update(iam_client_, iam_role_name_, trust_policy):
    """
    Perform the IAM role update workflow, including creating or attaching a role policy.

    Parameters:
    - iam_client_ (boto3.client): AWS IAM client.
    - iam_role_name_ (str): The name of the IAM role.
    - trust_policy_file_path (str): The file path to the trust policy document in JSON format.

    Returns:
    str: The ARN (Amazon Resource Name) of the IAM role with the attached policy.
    """
    # The id "role_arn" will be used on lambda deployment
    role_arn = try_attach_role_policy(
        iam_client_, iam_role_name_, trust_policy)

    return role_arn


def do_lambda_update(
    lambda_client_, func_description_, ecr_image_name_,
    aws_account_id_, aws_region_, role_arn_
):
    """
    Perform the Lambda function update workflow, including deploying a Lambda function with a new ECR image.

    Parameters:
    - lambda_client_ (boto3.client): AWS Lambda client.
    - func_description_ (str): The description of the Lambda function.
    - ecr_image_name_ (str): The name of the ECR repository.
    - aws_account_id_ (str): AWS account ID.
    - aws_region_ (str): AWS region.
    - role_arn_ (str): The ARN of the IAM role associated with the Lambda function.

    Returns:
    tuple: A tuple containing the Lambda function name and URI.
    """

    # Gets lambda function according to ecr image name
    lambda_function_name_ = get_lambda_function_name(ecr_image_name_)

    # Deletes lambda function according to ecr image name
    delete_lambda_function(lambda_client_, lambda_function_name_)

    # Deploys lambda function of ECR image
    deploy_lambda_function(
        lambda_client_, func_description_,
        aws_account_id_, aws_region_,
        ecr_image_name_, role_arn_
    )

    # Get the Lambda function ARN
    lambda_arn = get_lambda_arn(lambda_client_, lambda_function_name_)

    # Set up integration with the Lambda function
    lambda_uri = build_lambda_uri(aws_region_, lambda_arn)

    return lambda_function_name_, lambda_uri


def do_api_update(
    gateway_client_, aws_account_id_, aws_region_,
    lambda_uri_, lambda_function_name_,
    endpoint_, method_verb_, stage_name_, usage_constraints_
):
    """
    Perform the API Gateway update workflow, including deploying an API Gateway with a new Lambda integration.

    Parameters:
    - gateway_client_ (boto3.client): AWS API Gateway client.
    - aws_account_id_ (str): AWS account ID.
    - aws_region_ (str): AWS region.
    - lambda_uri_ (str): The URI of the Lambda function to integrate with.
    - lambda_function_name_ (str): The name of the Lambda function.
    - endpoint_ (str): The endpoint name.
    - method_verb_ (str): The HTTP method (HTTP verb) for the integration.
    - stage_name_ (str): The deployment stage of the API.
    - usage_constraints_ (dict): Usage constraints, including rate limits and quotas.

    Returns:
    dict: Information about the deployed API, including its URL, API key, usage plan ID, REST API ID, and ARN.
    """

    # Defines the name of the API (not public facing)
    rest_api_name_ = lambda_function_name_ + "-api"

    # Delete previous API Gateway
    # FIX: This is too harsh. Try update it!
    delete_apis_by_name(gateway_client_, rest_api_name_)

    # Deploys lambda function as API Gateway endpoint
    api_deployment_reponse = deploy_rest_api(
        gateway_client_, aws_account_id_, aws_region_,
        lambda_uri_, rest_api_name_, endpoint_, method_verb_,
        stage_name_, usage_constraints_,
    )

    return api_deployment_reponse


def do_api_allowance(l_client, lambda_function_name, api_arn):
    """
    Allow API Gateway to access a Lambda function by adding permission.

    Parameters:
    - l_client (boto3.client): AWS Lambda client.
    - lambda_function_name (str): The name of the Lambda function.
    - api_arn (str): The ARN (Amazon Resource Name) of the API Gateway.

    Returns:
    None
    """

    try:
        add_apigateway_permission(l_client, lambda_function_name, api_arn)
    except l_client.exceptions.ResourceConflictException:
        pass


@timing("Deployment of ML solution")
def deploy_solution(account_info, activity_info, configuration_paths):
    """
    Deploy a machine learning solution by updating ECR, IAM, Lambda, and API Gateway configurations.

    Parameters:
    - account_info (dict): Information about the AWS account, including account ID, region, and IAM role.
    - activity_info (dict): Information about the machine learning activity, including image name, Lambda function description, endpoint, method, and stage.
    - configuration_paths (dict): File paths for configuration files, including trust policy and usage constraints.

    Returns:
    dict: Information about the deployed solution, including API key, API URL, and HTTP method.
    """

    # AWS account information
    aws_account_id_ = account_info["account_id"]
    aws_region_ = account_info["region"]
    iam_role_name_ = account_info["iam_role"]

    # Set up the IAM client
    iam_client_ = client("iam", region_name=aws_region_)

    # Set up the Lambda client
    lambda_client_ = client("lambda", region_name=aws_region_)

    # Set up the API Gateway client
    gateway_client_ = client("apigateway", region_name=aws_region_)

    # Activity information
    ecr_image_name_ = activity_info["image_name"]
    func_description_ = activity_info["lambda_function_description"]
    endpoint_ = activity_info["endpoint"]
    method_verb_ = activity_info["method"]
    stage_name_ = activity_info["stage"]

    usage_constraints = configuration_paths["usage_constraints"]
    trust_policy = configuration_paths["trust_policy"]

    # Deployment pipeline steps:

    # 1. Creates docker image and uploads to ECR
    do_ecr_update(aws_account_id_, aws_region_, ecr_image_name_)

    # 2. Updates iam permissions
    role_arn_ = do_iam_update(iam_client_, iam_role_name_, trust_policy)

    # 3. Downloads respective ECR image and links to an
    lambda_function_name_, lambda_uri_ = do_lambda_update(
        lambda_client_, func_description_, ecr_image_name_,
        aws_account_id_, aws_region_, role_arn_
    )

    # 4. Updates API Gateway endpoint
    # Rate limits: Harsh since this will be public facing
    # Quota: Low daily limits for the same reason
    api_deployment_reponse = do_api_update(
        gateway_client_, aws_account_id_, aws_region_,
        lambda_uri_, lambda_function_name_,
        endpoint_, method_verb_, stage_name_, usage_constraints
    )

    # 5. Allow API Gateway to access Lambda function
    api_arn = api_deployment_reponse["arn"]
    do_api_allowance(lambda_client_, lambda_function_name_, api_arn)

    # Retrieve information from
    rest_api_id = api_deployment_reponse["rest_api_id"]
    api_key = api_deployment_reponse["api_key"]

    # The URL by default will follow this pattern:
    api_url = build_api_url(rest_api_id, aws_region_, endpoint_, stage_name_)

    return {
        "api_key": api_key,
        "api_url": api_url,
        "method_verb": method_verb_,
    }
