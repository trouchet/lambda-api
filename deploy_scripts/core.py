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
    # The id "role_arn" will be used on lambda deployment
    pipe_docker_image_to_ecr(aws_account_id_, aws_region_, ecr_image_name_)

def do_iam_update(iam_client_, iam_role_name_, trust_policy_file_path):
    trust_policy = get_trust_policy(trust_policy_file_path)
    
    # The id "role_arn" will be used on lambda deployment
    role_arn = try_attach_role_policy(iam_client_, iam_role_name_, trust_policy)
    
    return role_arn

def do_lambda_update(
    lambda_client_, func_description_, ecr_image_name_, \
    aws_account_id_, aws_region_, role_arn_
):
    # Gets lambda function according to ecr image name
    lambda_function_name_ = get_lambda_function_name(ecr_image_name_)

    # Deletes lambda function according to ecr image name
    delete_lambda_function(lambda_client_, lambda_function_name_)

    # Deploys lambda function of ECR image
    deploy_lambda_function(
            lambda_client_, func_description_, \
            aws_account_id_, aws_region_, \
            ecr_image_name_, role_arn_
    )
    
    # Get the Lambda function ARN
    lambda_arn = get_lambda_arn(lambda_client_, lambda_function_name_)

    # Set up integration with the Lambda function
    lambda_uri = build_lambda_uri(aws_region_, lambda_arn)
    
    return lambda_function_name_, lambda_uri
    
def do_api_update(
    gateway_client_, aws_account_id_, aws_region_, \
    lambda_uri_, lambda_function_name_, \
    endpoint_, method_verb_, stage_name_, usage_constraints_
):
    # Defines the name of the API (not public facing)
    rest_api_name_ = lambda_function_name_ + '-api'

    # Delete previous API Gateway
    # FIX: This is too harsh. Try update it! 
    delete_apis_by_name(gateway_client_, rest_api_name_)

    # Deploys lambda function as API Gateway endpoint
    api_deployment_reponse = deploy_rest_api(\
        gateway_client_, aws_account_id_, aws_region_, \
        lambda_uri_, rest_api_name_,  endpoint_, method_verb_, \
        stage_name_, usage_constraints_, 
    )
    
    return api_deployment_reponse

def do_api_allowance(l_client, lambda_function_name, api_arn):
    try: 
        add_apigateway_permission(l_client, lambda_function_name, api_arn)
    except l_client.exceptions.ResourceConflictException:
        pass

@timing('Deployment of ML solution')
def deploy_solution(account_info, activity_info, configuration_paths):
    # Extract metadata
    
    # AWS account information
    aws_account_id_=account_info['account_id']
    aws_region_=account_info['region']
    
    # Set up the IAM client
    iam_client_ = client('iam', region_name=aws_region_)

    # Set up the Lambda client
    lambda_client_ = client('lambda', region_name=aws_region_)

    # Set up the API Gateway client
    gateway_client_ = client('apigateway', region_name=aws_region_)


    # Activity information
    iam_role_name_=activity_info['iam_role']
    ecr_image_name_=activity_info['image_name']
    func_description_=activity_info['lambda_function_description']
    endpoint_=activity_info['endpoint']
    method_verb_=activity_info['method']
    stage_name_=activity_info['stage']
    
    usage_constraints_file_path=configuration_paths['usage_constraints']
    trust_policy_file_path=configuration_paths['trust_policy']
    
    # Deployment pipeline steps: 
    
    # 1. Creates docker image and uploads to ECR
    do_ecr_update(aws_account_id_, aws_region_, ecr_image_name_)
    
    # 2. Updates iam permissions
    role_arn_=do_iam_update(iam_client_, iam_role_name_, trust_policy_file_path)
    
    # 3. Downloads respective ECR image and links to an
    lambda_function_name_, lambda_uri_=do_lambda_update(
        lambda_client_, func_description_, ecr_image_name_, \
        aws_account_id_, aws_region_, role_arn_
    )
    
    # 4. Updates API Gateway endpoint
    ## Rate limits: Harsh since this will be public facing
    ## Quota: Low daily limits for the same reason
    usage_constraints = get_lambda_usage_constraints(usage_constraints_file_path)    
    
    api_deployment_reponse=do_api_update(
        gateway_client_, aws_account_id_, aws_region_,
        lambda_uri_, lambda_function_name_, 
        endpoint_, method_verb_, stage_name_, usage_constraints
    )
    
    # 5. Allow API Gateway to access Lambda function
    api_arn=api_deployment_reponse['arn']
    do_api_allowance(lambda_client_, lambda_function_name_, api_arn)
    
    # Retrieve information from 
    rest_api_id=api_deployment_reponse['rest_api_id']
    api_key=api_deployment_reponse['api_key']
    
    # The URL by default will follow this pattern:
    api_url = build_api_url(rest_api_id, aws_region_, endpoint_, stage_name_)
    
    return {
        'api_key': api_key,
        'api_url': api_url,
        'method_verb': method_verb_,
    }