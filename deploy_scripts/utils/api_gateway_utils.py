from .misc import timing
from .default_values import GATEWAY_DEPLOYMENT_SLEEP_SECONDS, \
    GATEWAY_DEPLOYMENT_UPDATE_DELAY_SECONDS

def build_source_arn(region_, account_id_, rest_api_id_):
    return f'arn:aws:execute-api:{region_}:{account_id_}:{rest_api_id_}/*'

def build_api_url(rest_api_id, region_, endpoint_, stage_):
    host=f"https://{rest_api_id}.execute-api.{region_}.amazonaws.com"
    route=f"{stage_}/{endpoint_}/"
    return f"{host}/{route}"

def delete_apis_by_name(api_gateway_client, rest_api_name):
    # Get all APIs
    response = api_gateway_client.get_rest_apis()

    for item in response['items']:
        if item['name'] == rest_api_name:
            # Delete the API by its ID
            api_id = item['id']
            api_gateway_client.delete_rest_api(restApiId=api_id)
            print(f"Deleted API with name '{rest_api_name}' and ID '{api_id}'")

def has_api(g_client, rest_api_name_):
    response = g_client.get_rest_apis()
    create_api_on_gateway = False
    
    for item in response['items']:
        if item['name'] == rest_api_name_:
            create_api_on_gateway = True
            
    return create_api_on_gateway

def create_resource(g_client, rest_api_id_, endpoint_):
    response = g_client.get_resources(restApiId=rest_api_id_)
    root_id = response['items'][0]['id']
    
    response = g_client.create_resource(
        restApiId=rest_api_id_,
        parentId=root_id,
        pathPart=endpoint_,
    )
    
    resource_id = response['id']
    
    return resource_id

def create_rest_method(g_client, rest_api_id_, resource_id_, method_verb_):
    g_client.put_method(
        restApiId=rest_api_id_,
        resourceId=resource_id_,
        httpMethod=method_verb_,
        authorizationType='NONE', # WARNING: this will allow public access!
        apiKeyRequired=True,
    )

def create_rest_api(g_client, rest_api_name_):
    description='API Gateway that triggers a lambda function'
    response=g_client.create_rest_api(name=rest_api_name_, description=description) 
    
    rest_api_id = response['id']
    
    return rest_api_id

def setup_integration(g_client, lambda_uri_, rest_api_id_, resource_id_, method_verb_):
    """
    Set up integration with API Gateway.

    Parameters:
    - g_client (boto3.client): AWS API Gateway client.
    - lambda_uri_ (str): The URI of the Lambda function to integrate with.
    - rest_api_id_ (str): The ID of the API Gateway REST API.
    - resource_id_ (str): The ID of the API Gateway resource.
    - method_verb_ (str): The HTTP method (HTTP verb) for the integration.
    
    Available HTTP Methods (method_verb_):
    - 'GET': Retrieve data from the resource.
    - 'POST': Submit data to the resource to be processed.
    - 'PUT': Update an existing resource or create a new one if it doesn't exist.
    - 'DELETE': Remove a resource.
    - 'PATCH': Partially update a resource.
    - 'OPTIONS': Retrieve information about communication options for the resource.
    - 'HEAD': Retrieve only the headers for the resource.
    - 'TRACE': Perform a message tracing of the resource.

    Example usage:
    setup_integration(\
        api_gateway_client, \
        'arn:aws:lambda:us-east-1:123456789012:function/my-lambda', \
        'api-id', \
        'resource-id', \
        'GET')
    """
    
    g_client.put_integration(
        restApiId=rest_api_id_,
        resourceId=resource_id_,
        httpMethod=method_verb_,
        type='AWS_PROXY',
        integrationHttpMethod=method_verb_,
        uri=lambda_uri_,
    )
    
def create_deployment(g_client, rest_api_id_, stage_):
    g_client.create_deployment(restApiId=rest_api_id_, stageName=stage_)
    
def create_api_key(g_client, rest_api_name_):
    response = g_client.create_api_key(
        name=rest_api_name_ + '-key',
        description='API key',
        enabled=True,
        generateDistinctId=True
    )
    
    api_key_id = response['id']
    api_key_value = response['value']
    
    return api_key_id, api_key_value

def create_usage_plan(g_client, rest_api_id_, stage_, usage_constraints_):
    name='API usage plan'
    description='Harsh rate limits and daily quota for public facing API'
    stages=[
        {
            'apiId': rest_api_id_,
            'stage': stage_,
        },
    ]
    
    response = g_client.create_usage_plan(
        name=name,
        description=description,
        apiStages=stages,
        throttle=usage_constraints_['rate_limits'],
        quota=usage_constraints_['quota']
    )
    
    usage_plan_id = response['id']
    
    return usage_plan_id

def create_usage_plan_key(g_client, usage_plan_id_, api_key_id_):
    g_client.create_usage_plan_key(
        usagePlanId=usage_plan_id_,
        keyId=api_key_id_,
        keyType='API_KEY'
    )
    
def add_apigateway_permission(l_client, function_name_, source_arn_):
    return l_client.add_permission(
        FunctionName=function_name_,
        StatementId='apigateway-lambda-invoke-permission',
        Action='lambda:InvokeFunction',
        Principal='apigateway.amazonaws.com',
        SourceArn=source_arn_
    )

def wait_for_api_endpoint(api_gateway_client, rest_api_id, stage_name):
    from time import sleep, time
    start_time = time()
    
    response = api_gateway_client.get_stage(restApiId=rest_api_id, stageName=stage_name)

    current_time=time()

    def is_api_available(response):
        last_update_time=response.get('lastUpdatedDate').timestamp()

        return current_time-last_update_time<=GATEWAY_DEPLOYMENT_UPDATE_DELAY_SECONDS

    while not is_api_available(response):
        try:
            response = api_gateway_client.get_stage(restApiId=rest_api_id, stageName=stage_name)
            if is_api_available(response):
                end_time = time()
                duration = end_time - start_time

                print(f"Endpoint is available at: {response['invokeUrl']}")
                print(f"APIEndpoint deployment duration: {duration:.2f} seconds")
                break
            else:
                print("Endpoint deployment is still in progress. Waiting...")
                
                # Wait for 10 seconds before checking again
                sleep(GATEWAY_DEPLOYMENT_SLEEP_SECONDS)
        
        except api_gateway_client.exceptions.NotFoundException:
            print("API Gateway stage not found. Waiting...")
            
            # Wait for 10 seconds before checking again
            sleep(GATEWAY_DEPLOYMENT_SLEEP_SECONDS)


def deploy_rest_api(g_client, account_id, region, \
        lambda_uri_, rest_api_name_, endpoint_, method_verb_, \
        stage_, api_usage_constraints_):
    # First, lets verify whether we already have an endpoint with this name.
    if not has_api(g_client, rest_api_name_):

        # 1. Create REST API
        rest_api_id = create_rest_api(g_client, rest_api_name_)

        # 2. Create resource
        resource_id=create_resource(g_client, rest_api_id, endpoint_)
        
        # 3. Create method
        create_rest_method(g_client, rest_api_id, resource_id, method_verb_)
        
        # 5. Set up integration with the Lambda function
        setup_integration(g_client, lambda_uri_, rest_api_id, resource_id, method_verb_)

        # 6. Deploy API
        create_deployment(g_client, rest_api_id, stage_)

        # 7. Create API key
        api_key_id, api_key_value = create_api_key(g_client, rest_api_name_)

        # 8. Create usage plan
        usage_plan_id = create_usage_plan(g_client, rest_api_id, stage_, api_usage_constraints_)
        
        # 9. Associate the usage plan with the API key
        create_usage_plan_key(g_client, usage_plan_id, api_key_id)
        
        # 10. Grant API Gateway permission to invoke the Lambda function
        this_api_arn = build_source_arn(region, account_id, rest_api_id)

        return {
            'url': build_api_url(rest_api_id, region, endpoint_, stage_),
            'api_key': api_key_value,
            'usage_plan_id': usage_plan_id,
            'rest_api_id': rest_api_id,
            'arn': this_api_arn
        }
    
    else: 
        failure_msg=f"REST API name {rest_api_name_} is already under usage!"
        print(failure_msg)
        
        return {}