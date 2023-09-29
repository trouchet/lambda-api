# Sleep interval in seconds between checks while waiting for Lambda deployment.
LAMBDA_SLEEP_SECONDS = 5

# Timeout duration in seconds for waiting for Lambda deployment.
LAMBDA_UPDATE_TIME_OUT_SECONDS = 600

# Sleep interval in seconds between checks while waiting for Gateway deployment.
GATEWAY_DEPLOYMENT_SLEEP_SECONDS = 1

# Delay in seconds before checking Gateway deployment status.
GATEWAY_DEPLOYMENT_UPDATE_DELAY_SECONDS = 600

# The default tag for AWS resources.
DEFAULT_TAG = "latest"

# The ARN (Amazon Resource Name) for the AWS Lambda execution role.
LAMBDA_POLICY_ARN = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

# Set to True to enable verbosity, False to disable.
IS_VERBOSE = False






