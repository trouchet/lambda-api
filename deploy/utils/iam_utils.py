from json import dumps

from .misc import timing, handle_aws_errors
from .default_values import LAMBDA_POLICY_ARN

@handle_aws_errors
def try_get_role(i_client, role_name_, trust_policy):
    """
    Try to get an AWS IAM role by name. If the role does not exist, create it.

    Parameters:
    - i_client (boto3.client): AWS IAM client.
    - role_name_ (str): The name of the IAM role.
    - trust_policy (dict): The trust policy document in JSON format.

    Returns:
    dict: Information about the IAM role.
    """
    

    try:
        return i_client.get_role(
            RoleName=role_name_
        )
    except i_client.exceptions.NoSuchEntityException:
        i_client.create_role(
            RoleName=role_name_,
            AssumeRolePolicyDocument=dumps(trust_policy),
            Description="Execution role for Lambda function",
        )


@timing("Role policy attachment")
def try_attach_role_policy(i_client, role_name_, trust_policy):
    """
    Try to attach an AWS managed policy to an existing IAM role. If the role does not exist, create it first.

    Parameters:
    - i_client (boto3.client): AWS IAM client.
    - role_name_ (str): The name of the IAM role.
    - trust_policy (dict): The trust policy document in JSON format.

    Returns:
    str: The ARN (Amazon Resource Name) of the IAM role with the attached policy.
    """

    # Just need to run it once, otherwise retrieve already existing role
    response = try_get_role(i_client, role_name_, trust_policy)

    # Get the role ARN
    role_arn = response["Role"]["Arn"]

    # Attach the AWSLambdaBasicExecutionRole policy to the role
    i_client.attach_role_policy(
        RoleName=role_name_,
        PolicyArn=LAMBDA_POLICY_ARN)

    return role_arn
