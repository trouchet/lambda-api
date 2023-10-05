from boto3 import client
from os import getenv
from dotenv import load_dotenv

from .utils.misc import get_lambda_usage_constraints, \
    get_trust_policy, get_calling_module_folder
from .utils.iam_utils import try_attach_role_policy
from .utils.ecr_utils import pipe_docker_image_to_ecr
from .utils.lambda_utils import update_or_deploy_lambda_function, \
    get_lambda_arn, \
    build_lambda_uri
from .utils.api_gateway_utils import deploy_rest_api, \
    add_apigateway_permission, \
    build_api_url
from .utils.misc import timing

@timing("ECR image upload")
def do_ecr_update(aws_account_id_, aws_region_, ecr_image_name_):
    """
    Perform the ECR update workflow, including creating and pushing a Docker image to AWS ECR.

    Parameters:
    - aws_account_id_ (str): AWS account ID.
    - aws_region_ (str): AWS region.
    - ecr_image_name_ (str): The name of the ECR repository.
    """

    # The id "role_arn" will be used on lambda deployment
    routed_url = pipe_docker_image_to_ecr(aws_account_id_, aws_region_, ecr_image_name_)

    return routed_url

@timing("IAM policies update")
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

@timing("Lambda function deployment")
def do_lambda_update(
    lambda_client_, routed_ecr_url_, \
    lambda_function_name_, lambda_function_description_, role_arn_
):
    """
    Update the Lambda function code with a new ECR image if it exists, or create it if it doesn't.

    Parameters:
    - lambda_client_ (boto3.client): AWS Lambda client.
    - routed_ecr_url_ (str): The uri of the ECR repository.
    - lambda_function_name_ (str): The name of the Lambda function.    
    - aws_account_id (str): AWS account ID.
    - aws_region (str): AWS region.
    - role_arn (str): The ARN of the IAM role associated with the Lambda function.

    Returns:
    tuple: A tuple containing the Lambda function name and URI.
    """

    update_or_deploy_lambda_function(\
        lambda_client_, lambda_function_name_, lambda_function_description_, \
        routed_ecr_url_, role_arn_
    )

    # Get the Lambda function ARN
    lambda_arn = get_lambda_arn(lambda_client_, lambda_function_name_)

    # Set up integration with the Lambda function
    aws_region_=lambda_client_.meta.region_name
    lambda_uri = build_lambda_uri(aws_region_, lambda_arn)

    return lambda_uri

@timing("API endpoint deployment")
def do_api_update(
    gateway_client_, aws_account_id_, aws_region_,
    lambda_uri_, lambda_function_name_,
    rest_api_name_, endpoint_, method_verb_, stage_name_, usage_constraints_
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
def deploy_api_endpoint(account_info, activity_info, configuration_info):
    """
    Deploy a machine learning solution by updating ECR, IAM, Lambda, and API Gateway configurations.

    Parameters:
    - account_info (dict): Information about the AWS account, including account ID, region, and IAM role.
    - activity_info (dict): Information about the machine learning activity, including image name, \
        Lambda function description, endpoint, method, and stage.
    - configuration_info (dict): Configuration objects (trust policy and usage constraints)

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
    lambda_function_name_ = activity_info["lambda_function_name"]
    lambda_function_description_ = activity_info["lambda_function_description"]
    rest_api_name_ = activity_info["rest_api_name"]
    endpoint_ = activity_info["endpoint"]
    method_verb_ = activity_info["method_verb"]
    stage_name_ = activity_info["stage"]

    usage_constraints = configuration_info["usage_constraints"]
    trust_policy = configuration_info["trust_policy"]

    # Deployment pipeline steps:

    # 1. Creates docker image and uploads to ECR
    routed_ecr_url = do_ecr_update(aws_account_id_, aws_region_, ecr_image_name_)

    # 2. Updates iam permissions
    role_arn_ = do_iam_update(iam_client_, iam_role_name_, trust_policy)
    
    # 3. Downloads respective ECR image and links to an
    lambda_uri_ = do_lambda_update(
        lambda_client_, routed_ecr_url, 
        lambda_function_name_, lambda_function_description_, role_arn_
    )

    # 4. Updates API Gateway endpoint
    # Rate limits: Harsh since this will be public facing
    # Quota: Low daily limits for the same reason
    api_deployment_reponse = do_api_update(
        gateway_client_, aws_account_id_, aws_region_,
        lambda_uri_, lambda_function_name_, rest_api_name_,
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


def do_deploy(account_info, activity_info_, configuration_info_):

    # Load environment variables from .env
    trust_policy_path=configuration_info_["trust_policy_path"]
    usage_constraints_path=configuration_info_["usage_constraints_path"]

    # Load environment variables from .env, usage constraints and trust policy
    usage_constraints = get_lambda_usage_constraints(usage_constraints_path)
    trust_policy = get_trust_policy(trust_policy_path)

    configuration={
        "usage_constraints": usage_constraints,
        "trust_policy": trust_policy
    }

    deployment_info = deploy_api_endpoint(account_info, activity_info_, configuration)

    return deployment_info

def deploy_application(info_environment_path):
    """
    Deploy an application by retrieving environment variables, constructing deployment information,
    and invoking the deployment process.

    Args:
        info_environment_path (str): The path to the environment file containing necessary information
            such as AWS account ID, region, IAM role name, ECR image name, Lambda function details,
            API Gateway details, and more.

    Returns:
        str: A message indicating the status of the deployment process.

    Example:
        # Deploy an application using the specified environment file
        result = deploy_application('/path/to/environment.env')
        print(result)

    Note:
        - The environment file should contain the following variables:
            - AWS_ACCOUNT_ID: AWS account ID
            - AWS_REGION: AWS region
            - IAM_ROLE_NAME: IAM role name
            - ECR_IMAGE_NAME: ECR image name
            - LAMBDA_NAME: Lambda function name
            - LAMBDA_DESCRIPTION: Lambda function description
            - LAMBDA_METHOD_VERB: Lambda function method verb
            - API_NAME: API Gateway name
            - API_STAGE: API Gateway stage
            - API_ENDPOINT: API Gateway endpoint

        - Additionally, ensure that trust_policy and api_usage_constraints files are present
          in the same directory as this script/module.

    """
    
    load_dotenv(info_environment_path)
    aws_account_id = getenv("AWS_ACCOUNT_ID")
    aws_region = getenv("AWS_REGION")
    iam_role_name = getenv("IAM_ROLE_NAME")

    ecr_image_name=getenv('ECR_IMAGE_NAME')

    lambda_name=getenv('LAMBDA_NAME')
    lambda_description=getenv('LAMBDA_DESCRIPTION')
    lambda_method_verb=getenv('LAMBDA_METHOD_VERB')
    
    api_name=getenv('API_NAME')
    api_stage=getenv('API_STAGE')
    api_endpoint=getenv('API_ENDPOINT')

    account_info={
        "account_id": aws_account_id,
        "region": aws_region,
        "iam_role":iam_role_name
    }

    activity_info = {
        'image_name': ecr_image_name,
        "lambda_function_name": lambda_name,
        'lambda_function_description': lambda_description,
        "rest_api_name": api_name,
        'stage': api_stage,
        'method_verb': lambda_method_verb,
        'endpoint': api_endpoint                
    }

    # Base folder for trust policy and usage constraints
    # NOTE: Files must have name as below:
    #   - api_usage_constraints;
    #   - trust_policy.
    calling_module_folder = get_calling_module_folder(__file__)
    
    configuration_info={
        'trust_policy_path': calling_module_folder,
        'usage_constraints_path': calling_module_folder
    }
    
    return do_deploy(account_info, activity_info, configuration_info)