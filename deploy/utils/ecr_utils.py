from .misc import timing
from .default_values import DEFAULT_TAG

def build_tagged_image(image_name, tag):
    """
    Build a tagged Docker image name.

    Parameters:
    image_name (str): The base Docker image name.
    tag (str): The tag to be appended to the image name.

    Returns:
    str: The tagged Docker image name.
    """

    return f"{image_name}:{tag}"


def build_ecr_password_stdin(account_id_, region_):
    """
    Build the password standard input for AWS ECR.

    Parameters:
    account_id_ (str): AWS account ID.
    region_ (str): AWS region.

    Returns:
    str: The ECR password standard input.
    """

    return f"{account_id_}.dkr.ecr.{region_}.amazonaws.com"


def build_ecr_url(account_id_, region_, image_name, tag_=DEFAULT_TAG):
    """
    Build the ECR URL for a Docker image.

    Parameters:
    account_id_ (str): AWS account ID.
    region_ (str): AWS region.
    image_name (str): The Docker image name.
    tag_ (str, optional): The Docker image tag (default is 'latest').

    Returns:
    str: The ECR URL for the Docker image.
    """

    tagged_image_name = build_tagged_image(image_name, tag_)
    password_stdin = build_ecr_password_stdin(account_id_, region_)

    return f"{password_stdin}/{tagged_image_name}"


def run(command, verbose=False):
    """
    Run a shell command.

    Parameters:
    command (str): The shell command to run.
    verbose (bool, optional): If True, run the command in verbose mode (default is False).
    
    Returns:
    dict: A dictionary containing 'stdout' and 'stderr' keys with the respective outputs.
    """
    import subprocess

    try:
        if (verbose):
            result = subprocess.run(command, shell=True, text=True)

        else:
            result = subprocess.run(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                shell=True,
                text=True
            )

        output = {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }

        return output
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return {"stdout": "", "stderr": str(e), "returncode": 1}

def login_ecr_docker(account_id, region):
    """
    Log in to AWS ECR for Docker image uploads.

    Parameters:
    account_id (str): AWS account ID.
    region (str): AWS region.
    """

    print("Logging in on ECR account...")

    password_stdin = build_ecr_password_stdin(account_id, region)

    opts = f"get-login-password --region {region}"
    get_pwd_command = f"aws ecr {opts}"

    opts = f"--username AWS --password-stdin {password_stdin}"
    login_command = f"docker login {opts}"

    entry_command = f"{get_pwd_command} | {login_command}"

    run(entry_command)


def create_ecr_image(ecr_image_name_):
    """
    Create an AWS ECR repository for a Docker image.

    Parameters:
    ecr_image_name_ (str): The name of the ECR repository.
    """

    print("Creating ECR image...")

    args_1 = f"--repository-name {ecr_image_name_}"
    args_2 = "--image-scanning-configuration scanOnPush=true"
    args_3 = "--image-tag-mutability MUTABLE"
    create_args = f"{args_1} {args_2} {args_3}"

    opts = f"create-repository {create_args}"
    create_comand = f"aws ecr {opts}"

    run(create_comand)

def does_ecr_image_exist(region, repository_name):
    from json import loads

    try:
        base_command="aws ecr"
        statement="describe-repositories"
        args=f"--repository-names {repository_name} --region {region}"
        command = f"{base_command} {statement} {args}"
        result = run(command)
        
        if result["returncode"] == 0:
            response_json = loads(result["stdout"])
            repositories = response_json.get("repositories", [])
            
            return len(repositories) > 0
        else:
            return False
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False

def delete_ecr_image(ecr_image_name_):
    """
    Delete an existing AWS ECR repository for a Docker image.

    Parameters:
    ecr_image_name_ (str): The name of the ECR repository.
    """

    print("Deleting existent ECR image...")

    tags = f"--force --repository-name {ecr_image_name_}"
    delete_command = f"aws ecr delete-repository {tags}"

    run(delete_command)


def build_docker_image(ecr_image_name):
    """
    Build a Docker image from a Dockerfile.

    Parameters:
    ecr_image_name (str): The name of the Docker image.
    """

    print("Building docker image...")

    build_args = f"-q -t {ecr_image_name} ."
    build_command = f"docker build {build_args}"

    run(build_command)


def tag_docker_image(tagged_image_uri_, routed_url):
    """
    Tag a Docker image with its URI.

    Parameters:
    tagged_image_uri_ (str): The tagged Docker image URI.
    routed_url (str): The ECR URL where the Docker image will be stored.
    """

    print("Tagging docker image...")

    tag_args = f"{tagged_image_uri_} {routed_url}"
    tag_command = f"docker tag {tag_args}"

    run(tag_command)


def push_docker_image(tagged_image_uri):
    """
    Push a Docker image to AWS ECR.

    Parameters:
    tagged_image_uri (str): The tagged Docker image URI.
    """

    print("Pushing docker image to ECR...")

    push_command = f"docker push {tagged_image_uri}"

    run(push_command)


@timing("Docker image upload on AWS ECR")
def pipe_docker_image_to_ecr(
    account_id_, region_, ecr_image_name_, tag_=DEFAULT_TAG
):
    """
    Upload a Docker image to AWS ECR.

    Parameters:
    account_id_ (str): AWS account ID.
    region_ (str): AWS region.
    ecr_image_name_ (str): The name of the ECR repository.
    tag_ (str, optional): The Docker image tag (default is 'latest').
    """

    # 1. Log in to AWS ECR
    login_ecr_docker(account_id_, region_)

    # 2. Check if the ECR repo already exists
    if not does_ecr_image_exist(region_, ecr_image_name_):
        # If it doesn't exist, create it
        create_ecr_image(ecr_image_name_)
    
    # 3. Build Docker image using your local Dockerfile
    build_docker_image(ecr_image_name_)

    # 4. Tag you image
    tagged_image_uri = build_tagged_image(ecr_image_name_, tag_)
    routed_url = build_ecr_url(account_id_, region_, ecr_image_name_, tag_)
    tag_docker_image(tagged_image_uri, routed_url)

    # 5. Push your image to ECR
    push_docker_image(routed_url)

    return routed_url
