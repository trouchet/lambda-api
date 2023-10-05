from botocore.exceptions import ClientError

from .default_values import GATEWAY_DEPLOYMENT_SLEEP_SECONDS, \
    GATEWAY_DEPLOYMENT_UPDATE_DELAY_SECONDS

from .misc import handle_aws_errors

def build_source_arn(region_, account_id_, rest_api_id_):
    """
    Build the Amazon Resource Name (ARN) for an API Gateway source.

    Parameters:
    - region_ (str): The AWS region where the API Gateway is located.
    - account_id_ (str): The AWS account ID.
    - rest_api_id_ (str): The ID of the API Gateway REST API.

    Returns:
    str: The constructed source ARN.
    """

    return f"arn:aws:execute-api:{region_}:{account_id_}:{rest_api_id_}/*"


def build_api_url(rest_api_id, region_, endpoint_, stage_):
    """
    Build the URL for an API Gateway endpoint.

    Parameters:
    - rest_api_id (str): The ID of the API Gateway REST API.
    - region_ (str): The AWS region where the API Gateway is located.
    - endpoint_ (str): The endpoint name.
    - stage_ (str): The deployment stage of the API.

    Returns:
    str: The constructed API URL.
    """

    protocol = "https"
    host_url = f"{rest_api_id}.execute-api.{region_}.amazonaws.com"
    host = f"{protocol}://{host_url}"
    route = f"{stage_}/{endpoint_}/"
    
    url=f"{host}/{route}"
    
    return url

@handle_aws_errors
def delete_apis_by_name(g_client, rest_api_name):
    """
    Delete API Gateway APIs with a given name.

    Parameters:
    - api_gateway_client (boto3.client): AWS API Gateway client.
    - rest_api_name (str): The name of the API to delete.

    Note:
    This function retrieves all APIs and deletes those with the specified name.
    """

    # Get all APIs
    response = g_client.get_rest_apis()

    for item in response["items"]:
        if item["name"] == rest_api_name:
            # Delete the API by its ID
            api_id = item["id"]
            g_client.delete_rest_api(restApiId=api_id)
            print(f"Deleted API with name '{rest_api_name}' and ID '{api_id}'")

@handle_aws_errors
def has_api(g_client, rest_api_name_):
    """
    Check if an API Gateway API with a given name exists.

    Parameters:
    - g_client (boto3.client): AWS API Gateway client.
    - rest_api_name_ (str): The name of the API to check.

    Returns:
    bool: True if the API exists, False otherwise.
    """

    response = g_client.get_rest_apis()
    create_api_on_gateway = False

    for item in response["items"]:
        if item["name"] == rest_api_name_:
            create_api_on_gateway = True

    return create_api_on_gateway



@handle_aws_errors
def get_rest_api_id_by_name(g_client, rest_api_name):
    """
    Get the ID of a REST API by its name.

    Parameters:
    - g_client (boto3.client): AWS API Gateway client.
    - rest_api_name (str): The name of the REST API to search for.

    Returns:
    str: The ID of the REST API if found, or None if not found.
    """
    response = g_client.get_rest_apis()
    
    for api in response["items"]:
        if api["name"] == rest_api_name:
            return api["id"]

    return None

@handle_aws_errors
def get_resource_id_by_name(g_client, rest_api_id, resource_name):
    """
    Get the ID of a resource within a REST API by its name.

    Parameters:
    - g_client (boto3.client): AWS API Gateway client.
    - rest_api_id (str): The ID of the REST API containing the resource.
    - resource_name (str): The name of the resource to search for.

    Returns:
    str: The ID of the resource if found, or None if not found.
    """
    response = g_client.get_resources(restApiId=rest_api_id)
    
    for resource in response["items"]:
        pathPart=resource.get('pathPart', '')

        if pathPart == resource_name:
            return resource["id"]

    return None

def create_endpoint_resource(g_client, rest_api_id_, endpoint_):
    """
    Create a resource within an API Gateway.

    Parameters:
    - g_client (boto3.client): AWS API Gateway client.
    - rest_api_id_ (str): The ID of the API Gateway REST API.
    - endpoint_ (str): The name of the resource to create.

    Returns:
    str: The ID of the created resource or the existing resource with the same name.
    """

    try:
        response = g_client.get_resources(restApiId=rest_api_id_)
        root_id = response["items"][0]["id"]

        response = g_client.create_resource(
            restApiId=rest_api_id_,
            parentId=root_id,
            pathPart=endpoint_,
        )

        resource_id = response["id"]
    except ClientError as e:
        error_reponse_code=e.response.get('Error', '').get('Code', '')
        if error_reponse_code == 'ConflictException':
            # Resource with the same name already exists, retrieve its ID
            existing_resource_name = endpoint_
            existing_resource_id = None
            
            # Find the existing resource ID
            for item in response["items"]:
                pathPart=item.get('pathPart', '')

                if pathPart == existing_resource_name:
                    existing_resource_id = item["id"]
                    break

            if existing_resource_id:
                resource_id = existing_resource_id
            else:
                # Handle the case where the existing resource ID is not found
                raise Exception("Existing resource ID not found")
        else:
            # Handle other AWS SDK errors
            raise e

    return resource_id

def create_rest_method(g_client, rest_api_id_, resource_id_, method_verb_):
    """
    Create an HTTP method (HTTP verb) for an API Gateway resource.

    Parameters:
    - g_client (boto3.client): AWS API Gateway client.
    - rest_api_id_ (str): The ID of the API Gateway REST API.
    - resource_id_ (str): The ID of the API Gateway resource.
    - method_verb_ (str): The HTTP method (HTTP verb) for the integration.
    """

    try:
        # Attempt to create the method
        g_client.put_method(
            restApiId=rest_api_id_,
            resourceId=resource_id_,
            httpMethod=method_verb_,
            authorizationType="NONE",  # WARNING: this will allow public access!
            apiKeyRequired=True,
        )
    except g_client.exceptions.ConflictException:
        # If the method already exists, we catch the ConflictException
        # and consider it as an update operation.
        pass


def create_rest_api(g_client, rest_api_name_):
    """
    Create a new API Gateway REST API.

    Parameters:
    - g_client (boto3.client): AWS API Gateway client.
    - rest_api_name_ (str): The name of the new API.

    Returns:
    str: The ID of the created API.
    """
    description = "API Gateway that triggers a lambda function"
    response = g_client.create_rest_api(
        name=rest_api_name_, description=description)

    rest_api_id = response["id"]

    return rest_api_id


def setup_integration(
        g_client,
        lambda_uri_,
        rest_api_id_,
        resource_id_,
        method_verb_):
    """
    Set up an integration between an AWS Lambda function and an AWS API Gateway resource.

    This function configures an integration that allows incoming HTTP requests to be proxied to the specified
    Lambda function for processing. The integration is associated with a specific API Gateway resource and
    HTTP method (HTTP verb).

    Parameters:
    - g_client (boto3.client): AWS API Gateway client.
    - lambda_uri_ (str): The URI of the Lambda function to integrate with, in the format:
      'arn:aws:lambda:<region>:<account_id>:function/<function_name>'.
    - rest_api_id_ (str): The ID of the AWS API Gateway REST API where the integration will be added.
    - resource_id_ (str): The ID of the API Gateway resource (e.g., endpoint or path) to associate with the
      integration.
    - method_verb_ (str): The HTTP method (HTTP verb) for which this integration should be configured. Accepted
      methods include 'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD', and 'TRACE'.

    Example usage:
    setup_integration(
        api_gateway_client,
        'arn:aws:lambda:us-east-1:123456789012:function/my-lambda',
        'api-id',
        'resource-id',
        'GET'
    )
    """

    g_client.put_integration(
        restApiId=rest_api_id_,
        resourceId=resource_id_,
        httpMethod=method_verb_,
        type="AWS_PROXY",
        integrationHttpMethod=method_verb_,
        uri=lambda_uri_,
    )

def check_stage_exists(g_client, rest_api_id_, stage_):
    """
    Check if a deployment stage already exists for an API Gateway.

    Parameters:
    - g_client (boto3.client): AWS API Gateway client.
    - rest_api_id_ (str): The ID of the API Gateway REST API.
    - stage_ (str): The deployment stage name.

    Returns:
    bool: True if the stage exists, False otherwise.
    """
    existing_deployments = g_client.get_deployments(restApiId=rest_api_id_)["items"]
    
    for deployment in existing_deployments:
        if "stageName" in deployment:
            if deployment["stageName"] == stage_:
                return True

    return False

def create_or_update_deployment(g_client, rest_api_id_, stage_):
    """
    Create or update a deployment for an API Gateway.

    Parameters:
    - g_client (boto3.client): AWS API Gateway client.
    - rest_api_id_ (str): The ID of the API Gateway REST API.
    - stage_ (str): The deployment stage name.
    """

    if check_stage_exists(g_client, rest_api_id_, stage_):
        # Update the existing deployment
        existing_deployments = g_client.get_deployments(restApiId=rest_api_id_)["items"]
        
        for deployment in existing_deployments:
            if deployment["stageName"] == stage_:
                g_client.update_deployment(
                    restApiId=rest_api_id_,
                    deploymentId=deployment["id"],
                    stageName=stage_
                )
                return
    else:
        # If no existing deployment with the specified stage, create a new one
        g_client.create_deployment(restApiId=rest_api_id_, stageName=stage_)


def create_api_key(g_client, rest_api_name_):
    """
    Create an API key for API Gateway.

    Parameters:
    - g_client (boto3.client): AWS API Gateway client.
    - rest_api_name_ (str): The name of the API for which to create the key.

    Returns:
    str: The ID of the created API key.
    str: The value of the created API key.
    """

    api_key_name = rest_api_name_ + "-key"

    # Check if an API key with the specified name already exists
    existing_keys = g_client.get_api_keys(
        nameQuery=api_key_name,
        includeValues=True
    )["items"]

    if existing_keys:
        api_key_id = existing_keys[0]["id"] 
        api_key_value = existing_keys[0]["value"]
         
    else:
        # If no API key exists, create a new one
        response = g_client.create_api_key(
            name=api_key_name,
            description="API key",
            enabled=True,
            generateDistinctId=True
        )

        api_key_id = response["id"]
        api_key_value = response["value"]

    return api_key_id, api_key_value

def add_apigateway_permission(l_client, function_name_, source_arn_):
    """
    Add an API Gateway permission to invoke a Lambda function.

    Parameters:
    - l_client (boto3.client): AWS Lambda client.
    - function_name_ (str): The name of the Lambda function.
    - source_arn_ (str): The Amazon Resource Name (ARN) of the API Gateway source.

    Returns:
    dict: The result of the `add_permission` operation.
    """
    try:
        l_client.add_permission(
            FunctionName=function_name_,
            StatementId="apigateway-lambda-invoke-permission",
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=source_arn_
        )
    except l_client.exceptions.ResourceConflictException:
        pass

def create_usage_plan(g_client, rest_api_id_, api_key_id, stage_, usage_constraints_):
    """
    Create an API usage plan for API Gateway.

    Parameters:
    - g_client (boto3.client): AWS API Gateway client.
    - rest_api_id_ (str): The ID of the API Gateway REST API.
    - stage_ (str): The deployment stage name.
    - usage_constraints_ (dict): Usage constraints, including rate limits and quotas.

    Returns:
    str: The ID of the created API usage plan.
    """

    name=usage_constraints_["name"]
    description=usage_constraints_["description"]
    stages = [
        {
            "apiId": rest_api_id_,
            "stage": stage_,
        },
    ]
    rate_limits=usage_constraints_["rate_limits"]
    quota=usage_constraints_["quota"]

    response = g_client.create_usage_plan(
        name=name,
        description=description,
        apiStages=stages,
        throttle=rate_limits,
        quota=quota
    )

    usage_plan_id = response["id"]

    try:
        g_client.create_usage_plan_key(
            usagePlanId=usage_plan_id,
            keyId=api_key_id,
            keyType="API_KEY"
        )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "ConflictException":
            # Handle the conflict (e.g., log it)
            print(f"{str(e)}")
        else:
            # Raise the exception for other errors
            raise e

    return usage_plan_id


def create_usage_plan_key(g_client, usage_plan_id_, api_key_id_):
    """
    Create an API key for an API usage plan in API Gateway.

    Parameters:
    - g_client (boto3.client): AWS API Gateway client.
    - usage_plan_id_ (str): The ID of the API usage plan.
    - api_key_id_ (str): The ID of the API key to associate with the plan.
    """

    g_client.create_usage_plan_key(
        usagePlanId=usage_plan_id_,
        keyId=api_key_id_,
        keyType="API_KEY"
    )


def wait_for_api_endpoint(api_gateway_client, rest_api_id, stage_name):
    """
    Wait for an API Gateway endpoint to become available.

    Parameters:
    - api_gateway_client (boto3.client): AWS API Gateway client.
    - rest_api_id (str): The ID of the API Gateway REST API.
    - stage_name (str): The name of the deployment stage.

    Note:
    This function waits for the endpoint to become available and prints the URL when ready.
    """

    from time import sleep, time
    start_time = time()

    response = api_gateway_client.get_stage(
        restApiId=rest_api_id, stageName=stage_name)

    current_time = time()
    def is_api_available(response):
        """
        Check if an API Gateway deployment is available based on its last update time.

        Compares the last update time of the deployment with the current time.
        Returns True if within a specified delay threshold, otherwise False.

        Parameters:
        - response (dict): API Gateway deployment response.

        Returns:
        bool: True if the API Gateway deployment is available, False otherwise.
        """

        last_update_time = response.get("lastUpdatedDate").timestamp()

        return current_time - last_update_time <= GATEWAY_DEPLOYMENT_UPDATE_DELAY_SECONDS

    while not is_api_available(response):
        try:
            response = api_gateway_client.get_stage(
                restApiId=rest_api_id, stageName=stage_name)
            if is_api_available(response):
                end_time = time()
                duration = end_time - start_time

                print(f"API Endpoint is available at: {response['invokeUrl']}")
                print(
                    f"API Endpoint deployment duration: {duration:.2f} seconds")
                break
            else:
                print("API Endpoint deployment is still in progress. Waiting...")

                # Wait for 10 seconds before checking again
                sleep(GATEWAY_DEPLOYMENT_SLEEP_SECONDS)

        except api_gateway_client.exceptions.NotFoundException:
            print("API Gateway stage not found. Waiting...")

            # Wait for 10 seconds before checking again
            sleep(GATEWAY_DEPLOYMENT_SLEEP_SECONDS)

def deploy_rest_api(g_client, account_id, region,
                    lambda_uri_, rest_api_name_, endpoint_, method_verb_,
                    stage_, api_usage_constraints_):
    """
    Deploy a REST API with AWS API Gateway.

    Parameters:
    - g_client (boto3.client): AWS API Gateway client.
    - account_id (str): The AWS account ID.
    - region (str): The AWS region.
    - lambda_uri_ (str): The URI of the Lambda function to integrate with.
    - rest_api_name_ (str): The name of the REST API.
    - endpoint_ (str): The endpoint name.
    - method_verb_ (str): The HTTP method (HTTP verb) for the integration.
    - stage_ (str): The deployment stage of the API.
    - api_usage_constraints_ (dict): Usage constraints, including rate limits and quotas.

    Returns:
    dict: Information about the deployed API, including its URL, API key, usage plan ID, REST API ID, and ARN.
    """

    # 1.a. Check if the API already exists
    rest_api_id = get_rest_api_id_by_name(g_client, rest_api_name_)

    # 1.b. If the API doesn't exist, create it
    if not rest_api_id:
        rest_api_id = create_rest_api(g_client, rest_api_name_)
    
    # 2. Create or retrieve REST resource
    resource_id = get_resource_id_by_name(g_client, rest_api_id, endpoint_)
    if not resource_id:
        # If the resource doesn't exist, create it
        resource_id = create_endpoint_resource(g_client, rest_api_id, endpoint_)

    # 3. Create REST method
    create_rest_method(g_client, rest_api_id, resource_id, method_verb_)

    # 4. Set up integration with the Lambda function
    setup_integration(g_client, lambda_uri_, rest_api_id, resource_id, method_verb_)
    
    # 5. Create or update API stage
    create_or_update_deployment(g_client, rest_api_id, stage_)

    # 6. Create API key
    api_key_id, api_key_value = create_api_key(g_client, rest_api_name_)

    # 7. Create usage plan
    usage_plan_id = create_usage_plan(
        g_client, rest_api_id, api_key_id, stage_, api_usage_constraints_)
    
    # 8. Grant API Gateway permission to invoke the Lambda function
    this_api_arn = build_source_arn(region, account_id, rest_api_id)

    return {
        "url": build_api_url(rest_api_id, region, endpoint_, stage_),
        "api_key": api_key_value,
        "usage_plan_id": usage_plan_id,
        "rest_api_id": rest_api_id,
        "arn": this_api_arn
    }

