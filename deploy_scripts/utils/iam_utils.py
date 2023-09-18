from json import dumps

from .misc import print_start_message, print_success_message
from .default_values import DEFAULT_TAG

def try_get_role(i_client, role_name_, trust_policy):
    try:
        return i_client.get_role(
            RoleName=role_name_
        )
    except i_client.exceptions.NoSuchEntityException:
        i_client.create_role(
            RoleName=role_name_,
            AssumeRolePolicyDocument=dumps(trust_policy),
            Description='Execution role for Lambda function',
        )

## AWS Lambda execution role 
lambda_policy_arn = 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        
def try_attach_role_policy(i_client, role_name_, trust_policy):
    task_name=f"Role policy attachment"
    
    print_start_message(task_name)

    # Just need to run it once, otherwise retrieve already existing role
    response=try_get_role(i_client, role_name_, trust_policy)

    # Get the role ARN
    role_arn = response['Role']['Arn']

    # Attach the AWSLambdaBasicExecutionRole policy to the role
    i_client.attach_role_policy(RoleName=role_name_, PolicyArn=lambda_policy_arn)
    
    print_success_message(task_name)

    return role_arn

