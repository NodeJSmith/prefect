---
description: Prefect deployments encapsulate a flow, allowing flow runs to be scheduled and triggered via API. Learn how to easily manage your code and deployments.
tags:
    - orchestration
    - deploy
    - CLI
    - flow runs
    - deployments
    - schedules
    - triggers
    - prefect.yaml
    - infrastructure
    - storage
    - work pool
    - worker
search:
  boost: 2
---

# Deploying Flows to Work Pools and Workers

In this guide, we will configure a deployment that uses a work pool for dynamically provisioned infrastructure.

All Prefect flow runs are tracked by the API. The API does not require prior registration of flows.
With Prefect, you can call a flow locally or on a remote environment and it will be tracked.

A deployment turns your workflow into an application that can be interacted with and managed via the Prefect API.
A deployment enables you to:

- Schedule flow runs.
- Specify event triggers for flow runs.
- Assign one or more tags to organize your deployments and flow runs. You can use those tags as filters in the Prefect UI.
- Assign custom parameter values for flow runs based on the deployment.
- Create ad-hoc flow runs from the API or Prefect UI.
- Upload flow files to a defined storage location for retrieval at run time.

!!! note "Deployments created with `.serve`"
    A deployment created with the Python `flow.serve` method or the `serve` function runs flows in a subprocess on the same machine where the deployment is created. It does not use a work pool or worker.

## Work pool-based deployments

A work pool-based deployment is useful when you want to dynamically scale the infrastructure where your flow code runs.
Work pool-based deployments contain information about the infrastructure type and configuration for your workflow execution.

Work pool-based deployment infrastructure options include the following:

- Process - runs flow in a subprocess. In most cases, you're better off using `.serve`.
- [Docker](/guides/deployment/docker/) - runs flows in an ephemeral Docker container.
- [Kubernetes](/guides/deployment/kubernetes/) - runs flows as a Kubernetes Job.
- [Serverless Cloud Provider options](/guides/deployment/serverless-workers/) - runs flows in a Docker container in a serverless cloud provider environment, such as AWS ECS, Azure Container Instance, Google Cloud Run, or Vertex AI.

The following diagram provides a high-level overview of the conceptual elements involved in defining a work-pool based deployment that is polled by a worker and executes a flow run based on that deployment.

```mermaid
%%{
  init: {
    'theme': 'base',
    'themeVariables': {
      'fontSize': '19px'
    }
  }
}%%

flowchart LR
    F("<div style='margin: 5px 10px 5px 5px;'>Flow Code</div>"):::yellow -.-> A("<div style='margin: 5px 10px 5px 5px;'>Deployment Definition</div>"):::gold
    subgraph Server ["<div style='width: 150px; text-align: center; margin-top: 5px;'>Prefect API</div>"]
        D("<div style='margin: 5px 10px 5px 5px;'>Deployment</div>"):::green
    end
    subgraph Remote Storage ["<div style='width: 160px; text-align: center; margin-top: 5px;'>Remote Storage</div>"]
        B("<div style='margin: 5px 6px 5px 5px;'>Flow</div>"):::yellow
    end
    subgraph Infrastructure ["<div style='width: 150px; text-align: center; margin-top: 5px;'>Infrastructure</div>"]
        G("<div style='margin: 5px 10px 5px 5px;'>Flow Run</div>"):::blue
    end

    A --> D
    D --> E("<div style='margin: 5px 10px 5px 5px;'>Worker</div>"):::red
    B -.-> E
    A -.-> B
    E -.-> G

    classDef gold fill:goldenrod,stroke:goldenrod,stroke-width:4px,color:black
    classDef yellow fill:gold,stroke:gold,stroke-width:4px,color:black
    classDef gray fill:lightgray,stroke:lightgray,stroke-width:4px
    classDef blue fill:blue,stroke:blue,stroke-width:4px,color:white
    classDef green fill:green,stroke:green,stroke-width:4px,color:white
    classDef red fill:red,stroke:red,stroke-width:4px,color:white
    classDef dkgray fill:darkgray,stroke:darkgray,stroke-width:4px,color:white
```

The work pool types above require a worker to be running on your infrastructure to poll a work pool for scheduled flow runs.

!!!note "Additional work pool options available with Prefect Cloud"

    Prefect Cloud offers other flavors of work pools that don't require a worker:

    - [Push Work Pools](/guides/deployment/push-work-pools) - serverless cloud options that don't require a worker because Prefect Cloud submits them to your serverless cloud infrastructure on your behalf. Prefect can auto-provision your cloud infrastructure for you and set it up to use your work pool.
    
    - [Managed Execution](/guides/managed-execution/) Prefect Cloud submits and runs your deployment on serverless infrastructure. No cloud provider account required.

In this guide, we focus on deployments that require a worker.

Work pool-based deployments that use a worker also allow you to assign a work queue name to prioritize work and allow you to limit concurrent runs at the work pool level.

When creating a deployment that uses a work pool and worker, we must answer _two_ basic questions:

- What instructions does a [worker](/concepts/work-pools/) need to set up an execution environment for our flow? For example, a flow may have Python package requirements, unique Kubernetes settings, or Docker networking configuration.
- How should the flow code be accessed?

## Creating work pool-based deployments

The [tutorial](/tutorial/deployments/) shows how you can create a deployment with a long-running process using `.serve` and how to move to a [work-pool-based deployment](/tutorial/workers/) setup with `.deploy`.
See the discussion of when you might want to move to work-pool-based deployments [there](/tutorial/workers/#why-workers-and-work-pools).

In this guide, we show how to use `.deploy` in more depth and discuss `prefect.yaml`, a YAML-based alternative for managing deployments.

Use the tabs below to explore these two deployment creation options.

=== ".deploy"

    ### Automatically bake your code into a Docker image 

    You can create a deployment from Python code by calling the `.deploy` method on a flow.

    ```python hl_lines="17-22" title="buy.py"
    from prefect import flow


    @flow(log_prints=True)
    def buy():
        print("Buying securities")


    if __name__ == "__main__":
        buy.deploy(
            name="my-code-baked-into-an-image-deployment", 
            work_pool_name="my-docker-pool", 
            image="my_registry/my_image:my_image_tag"
        )
    ```

    Make sure you have the [work pool](/concepts/work-pools/) created in the Prefect Cloud workspace you are authenticated to or on your running self-hosted server instance.  
    Then run the script to create a deployment (in future examples this step will be omitted for brevity):

    <div class="terminal">
    ```bash
    python buy.py
    ```
    </div>

    You should see messages in your terminal that Docker is building your image.
    When the deployment build succeeds you will see helpful information in your terminal showing you how to start a worker for your deployment and how to run your deployment.
    Your deployment will be visible on the `Deployments` page in the UI.

    By default, `.deploy` will build a Docker image with your flow code baked into it and push the image to the [Docker Hub](https://hub.docker.com/) registry specified in the `image` argument`. 
    
    !!! note "Authentication to Docker Hub"
        You need your environment to be authenticated to your Docker registry to push an image to it.

    You can specify a registry other than Docker Hub by providing the full registry path in the `image` argument.

    !!! warning
        If building a Docker image, the environment in which you are creating the deployment needs to have Docker installed and running.

    To avoid pushing to a registry, set `push=False` in the `.deploy` method.
    
    ```python hl_lines="6"

    if __name__ == "__main__":
        buy.deploy(
            name="my-code-baked-into-an-image-deployment", 
            work_pool_name="my-docker-pool", 
            image="my_registry/my_image:my_image_tag",
            push=False
        )
    ```

    To avoid building an image, set `build=False` in the `.deploy` method.

    ```python hl_lines="6"

    if __name__ == "__main__":
        buy.deploy(
            name="my-code-baked-into-an-image-deployment", 
            work_pool_name="my-docker-pool", 
            image="discdiver/no-build-image:1.0",
            build=False
        )
    ```

    The specified image will need to be available in your deployment's execution environment for your flow code to be accessible.

    Prefect generates a Dockerfile for you that will build an image based off of one of Prefect's published images. The generated Dockerfile will copy the current directory into the Docker image and install any dependencies listed in a `requirements.txt` file.

    ### Automatically build a custom Docker image with a local Dockerfile

    If you want to use a custom Dockerfile, you can specify the path to the Dockerfile with the `DeploymentImage` class:

    ```python hl_lines="14-17" title="custom_dockerfile.py"
    from prefect import flow
    from prefect.deployments import DeploymentImage


    @flow(log_prints=True)
    def buy():
        print("Selling securities")


    if __name__ == "__main__":
        buy.deploy(
            name="my-custom-dockerfile-deployment", 
            work_pool_name="my-docker-pool", 
            image=DeploymentImage(
                name="my_image",
                tag="deploy-guide",
                dockerfile="Dockerfile"
        ),
        push=False
    )

    ```
    
    The `DeploymentImage` object allows for a great deal of image customization.
    
    For example, you can install a private Python package from GCP's artifact registry like this:
   
    Create a custom base Dockerfile.

    ```
    FROM python:3.10

    ARG AUTHED_ARTIFACT_REG_URL
    COPY ./requirements.txt /requirements.txt

    RUN pip install --extra-index-url ${AUTHED_ARTIFACT_REG_URL} -r /requirements.txt
    ```

    Create our deployment by leveraging the DeploymentImage class. 

    ```python hl_lines="2 18-22" title="private-package.py"
    from prefect import flow
    from prefect.deployments.runner import DeploymentImage
    from prefect.blocks.system import Secret
    from my_private_package import do_something_cool


    @flow(log_prints=True)
    def my_flow():
        do_something_cool()


    if __name__ == "__main__":
        artifact_reg_url: Secret = Secret.load("artifact-reg-url")
        
        my_flow.deploy(
            name="my-deployment",
            work_pool_name="k8s-demo",
            image=DeploymentImage(
                name="my-image",
                tag="test",
                dockerfile="Dockerfile",
                buildargs={"AUTHED_ARTIFACT_REG_URL": artifact_reg_url.get()},
            ),
        )
    ```

    Note that we used a [Prefect Secret block](/concepts/blocks/) to load the URL configuration for the artifact registry above.

    See all the optional keyword arguments for the DeploymentImage class [here](https://docker-py.readthedocs.io/en/stable/images.html#docker.models.images.ImageCollection.build). 

    !!! tip "Default Docker namespace"
        You can set the `PREFECT_DEFAULT_DOCKER_BUILD_NAMESPACE` setting to append a default Docker namespace to all images you build with `.deploy`. This is great if you use a private registry to store your images.

        To set a default Docker namespace for your current profile run:

        <div class="terminal">
        ```bash
        prefect config set PREFECT_DEFAULT_DOCKER_BUILD_NAMESPACE=<docker-registry-url>/<organization-or-username>
        ```
        </div>

        Once set, you can omit the namespace from your image name when creating a deployment:

        ```python hl_lines="5" title="with_default_docker_namespace.py"
        if __name__ == "__main__":
            buy.deploy(
                name="my-code-baked-into-an-image-deployment", 
                work_pool_name="my-docker-pool", 
                image="my_image:my_image_tag"
            )
        ```

        The above code will build an image with the format `<docker-registry-url>/<organization-or-username>/my_image:my_image_tag` when `PREFECT_DEFAULT_DOCKER_BUILD_NAMESPACE` is set.

    While baking code into Docker images is a popular deployment option, many teams decide to store their workflow code in git-based storage, such as GitHub, Bitbucket, or Gitlab. Let's see how to do that next.

    ### Store your code in git-based cloud storage 

    If you don't specify an `image` argument for `.deploy`, then you need to specify where to pull the flow code from at runtime with the `from_source` method. 

    Here's how we can pull our flow code from a GitHub repository.

    ```python hl_lines="4-6" title="git_storage.py" 
    from prefect import flow

    if __name__ == "__main__":
        flow.from_source(
            "https://github.com/my_github_account/my_repo/my_file.git",
            entrypoint="flows/no-image.py:hello_world",
        ).deploy(
            name="no-image-deployment",
            work_pool_name="my_pool",
            build=False
        )
    ```

    The `entrypoint` is the path to the file the flow is located in and the function name, separated by a colon.

    Alternatively, you could specify a git-based cloud storage URL for a Bitbucket or Gitlab repository. 

    !!! note 
        If you don't specify an image as part of your deployment creation, the image specified in the work pool will be used to run your flow.

    After creating a deployment you might change your flow code. 
    Generally, you can just push your code to GitHub, without rebuilding your deployment. 
    The exception is if something that the server needs to know about changes, such as the flow entrypoint parameters. 
    Rerunning the Python script with `.deploy` will update your deployment on the server with the new flow code.

    If you need to provide additional configuration, such as specifying a private repository, you can provide a [`GitRepository`](/api-ref/prefect/flows/#prefect.runner.storage.GitRepository) object instead of a URL:

    ```python hl_lines="2-3 7-12" title="private_git_storage.py"
    from prefect import flow
    from prefect.runner.storage import GitRepository
    from prefect.blocks.system import Secret

    if __name__ == "__main__":
        flow.from_source(
            source=GitRepository(
            url="https://github.com/org/private-repo.git",
            branch="dev",
            credentials={
                "access_token": Secret.load("github-access-token")
            }
        ),
        entrypoint="flows/no-image.py:hello_world",
        ).deploy(
            name="private-git-storage-deployment",
            work_pool_name="my_pool",
            build=False
        )
    ```

    Note the use of the Secret block to load the GitHub access token. 
    Alternatively, you could provide a username and password to the `username` and `password` fields of the `credentials` argument.

    ### Store your code in cloud provider storage 

    Another option for flow code storage is any [fsspec](https://filesystem-spec.readthedocs.io/en/latest/)-supported storage location, such as AWS S3, GCP GCS, or Azure Blob Storage.

    For example, you can pass the S3 bucket path to `source`.

    ```python hl_lines="4-6" title="s3_storage.py"
    from prefect import flow

    if __name__ == "__main__":
        flow.from_source(
            source="s3://my-bucket/my-folder",
            entrypoint="flows.py:my_flow",
        ).deploy(
            name="deployment-from-aws-flow",
            work_pool="my_pool",
        )
    ```

    In the example above your credentials will be auto-discovered from your deployment creation environment and credentials will need to be available in your runtime environment.

    If you need additional configuration for your cloud-based storage - for example, with a private S3 Bucket -  we recommend using a [storage block](/concepts/blocks/). 
    A storage block also ensures your credentials will be available in both your deployment creation environment and your execution environment.

    Here's an example that uses an `S3Bucket` block from the [prefect-aws library](https://prefecthq.github.io/prefect-aws/).

    ```python hl_lines="2 5-7" title="s3_storage_auth.py"
    from prefect import flow
    from prefect_aws.s3 import S3Bucket

    if __name__ == "__main__":
        flow.from_source(
            source=S3Bucket.load("my-code-storage"), entrypoint="my_file.py:my_flow"
        ).deploy(name="test-s3", work_pool="my_pool")
    ```
    
    If you are familiar with the deployment creation mechanics with `.serve`, you will notice that `.deploy` is very similar. `.deploy` just requires a work pool name and has a number of parameters dealing with flow-code storage for Docker images. 

    Unlike `.serve`, if you don't specify an image to use for your flow, you must to specify where to pull the flow code from at runtime with the `from_source` method, whereas `from_source` is optional with `.serve`.


    ### Additional configuration with `.deploy`

    Our examples thus far have explored options for where to store flow code. 
    Let's turn our attention to other deployment configuration options.

    To pass parameters to your flow, you can use the `parameters` argument in the `.deploy` method. Just pass in a dictionary of key-value pairs.

    ```python hl_lines="11" title="pass_params.py"
    from prefect import flow

    @flow
    def hello_world(name: str):
        print(f"Hello, {name}!")

    if __name__ == "__main__":
        hello_world.deploy(
            name="pass-params-deployment",
            work_pool_name="my_pool",
            parameters=dict(name="Prefect"),
            image="my_registry/my_image:my_image_tag",
        )
    ```

    The `job_variables` parameter allows you to fine-tune the infrastructure settings for a deployment. 
    The values passed in override default values in the specified work pool's [base job template](/concepts/work-pools/#base-job-template).
    
    You can override environment variables, such as `image_pull_policy` and `image`, for a specific deployment with the `job_variables` argument. 

    ```python hl_lines="5" title="job_var_image_pull.py"
    if __name__ == "__main__":
        get_repo_info.deploy(
            name="my-deployment-never-pull", 
            work_pool_name="my-docker-pool", 
            job_variables={"image_pull_policy": "Never"},
            image="my-image:my-tag"",
            push=False
        )
    ```

    Similarly, you can override the environment variables specified in a work pool through the `job_variables` parameter:

    ```python hl_lines="5" title="job_var_env_vars.py"
    if __name__ == "__main__":
        get_repo_info.deploy(
            name="my-deployment-never-pull", 
            work_pool_name="my-docker-pool", 
            job_variables={"env": {"EXTRA_PIP_PACKAGES": "boto3"} },
            image="my-image:my-tag"",
            push=False
        )
    ```

    The dictionary key "EXTRA_PIP_PACKAGES" denotes a special environment variable that Prefect will use to install additional Python packages at runtime. 
    This approach is an alternative to building an image with a custom `requirements.txt` copied into it.

    For more information on overriding job variables see this [guide](/guides/deployment/overriding-job-variables/).

=== "prefect.yaml"

    The `prefect.yaml` file is a YAML file describing base settings for your deployments, procedural steps for preparing deployments, and instructions for preparing the execution environment for a deployment run.

    You can initialize your deployment configuration, which creates the `prefect.yaml` file, by running the CLI command `prefect init` in any directory or repository that stores your flow code.

    !!! tip "Deployment configuration recipes"
        Prefect ships with many off-the-shelf "recipes" that allow you to get started with more structure within your `prefect.yaml` file; run `prefect init` to be prompted with available recipes in your installation. You can provide a recipe name in your initialization command with the `--recipe` flag, otherwise Prefect will attempt to guess an appropriate recipe based on the structure of your working directory (for example if you initialize within a `git` repository, Prefect will use the `git` recipe).

    The `prefect.yaml` file contains deployment configuration for deployments created from this file, default instructions for how to build and push any necessary code artifacts (such as Docker images), and default instructions for pulling a deployment in remote execution environments (e.g., cloning a GitHub repository).

    Any deployment configuration can be overridden via options available on the `prefect deploy` CLI command when creating a deployment.

    !!! tip "`prefect.yaml` file flexibility"
        In older versions of Prefect, this file had to be in the root of your repository or project directory and named `prefect.yaml`. Now this file can be located in a directory outside the project or a subdirectory inside the project. It can be named differently, provided the filename ends in `.yaml`. You can even have multiple `prefect.yaml` files with the same name in different directories. By default, `prefect deploy` will use a `prefect.yaml` file in the project's root directory. To use a custom deployment configuration file, supply the new  `--prefect-file` CLI argument when running the `deploy` command from the root of your project directory: 
        
        `prefect deploy --prefect-file path/to/my_file.yaml`

    The base structure for `prefect.yaml` is as follows:

    ```yaml
    # generic metadata
    prefect-version: null
    name: null

    # preparation steps
    build: null
    push: null

    # runtime steps
    pull: null

    # deployment configurations
    deployments:
    - # base metadata
        name: null
        version: null
        tags: []
        description: null
        schedule: null

        # flow-specific fields
        entrypoint: null
        parameters: {}

        # infra-specific fields
        work_pool:
        name: null
        work_queue_name: null
        job_variables: {}
    ```

    The metadata fields are always pre-populated for you. These fields are for bookkeeping purposes only.  The other sections are pre-populated based on recipe; if no recipe is provided, Prefect will attempt to guess an appropriate one based on local configuration.

    You can create deployments via the CLI command `prefect deploy` without ever needing to alter the `deployments` section of your `prefect.yaml` file — the `prefect deploy` command will help in deployment creation via interactive prompts. The `prefect.yaml` file facilitates version-controlling your deployment configuration and managing multiple deployments.

    ### Deployment actions

    Deployment actions defined in your `prefect.yaml` file control the lifecycle of the creation and execution of your deployments.
    The three actions available are `build`, `push`, and `pull`.
    `pull` is the only required deployment action — it is used to define how Prefect will pull your deployment in remote execution environments.

    Each action is defined as a list of steps that are executing in sequence.

    Each step has the following format:

    ```yaml
    section:
    - prefect_package.path.to.importable.step:
        id: "step-id" # optional
        requires: "pip-installable-package-spec" # optional
        kwarg1: value
        kwarg2: more-values
    ```

    Every step can optionally provide a `requires` field that Prefect will use to auto-install in the event that the step cannot be found in the current environment. Each step can also specify an `id` for the step which is used when referencing step outputs in later steps. The additional fields map directly onto Python keyword arguments to the step function. Within a given section, steps always run in the order that they are provided within the `prefect.yaml` file.

    !!! tip "Deployment Instruction Overrides"
        `build`, `push`, and `pull` sections can all be overridden on a per-deployment basis by defining `build`, `push`, and `pull` fields within a deployment definition in the `prefect.yaml` file.

        The `prefect deploy` command will use any `build`, `push`, or `pull` instructions provided in a deployment's definition in the `prefect.yaml` file.

        This capability is useful with multiple deployments that require different deployment instructions.

    ### The build action

    The build section of `prefect.yaml` is where any necessary side effects for running your deployments are built - the most common type of side effect produced here is a Docker image. If you initialize with the docker recipe, you will be prompted to provide required information, such as image name and tag:

    <div class="terminal">
    ```bash
    prefect init --recipe docker
    >> image_name: < insert image name here >
    >> tag: < insert image tag here >
    ```
    </div>

    !!! tip "Use `--field` to avoid the interactive experience"
        We recommend that you only initialize a recipe when you are first creating your deployment structure, and afterwards store your configuration files within version control.
        However, sometimes you may need to initialize programmatically and avoid the interactive prompts.  
        To do so, provide all required fields for your recipe using the `--field` flag:
        
        <div class="terminal">
        ```bash
        prefect init --recipe docker \
            --field image_name=my-repo/my-image \
            --field tag=my-tag
        ```
        </div>

    ```yaml
    build:
    - prefect_docker.deployments.steps.build_docker_image:
        requires: prefect-docker>=0.3.0
        image_name: my-repo/my-image
        tag: my-tag
        dockerfile: auto
        push: true
    ```

    Once you've confirmed that these fields are set to their desired values, this step will automatically build a Docker image with the provided name and tag and push it to the repository referenced by the image name.  
    [As the `prefect-docker` package documentation notes](https://prefecthq.github.io/prefect-docker/deployments/steps/#prefect_docker.deployments.steps.BuildDockerImageResult), this step produces a few fields that can optionally be used in future steps or within `prefect.yaml` as template values.  
    It is best practice to use `{{ image }}` within `prefect.yaml` (specifically the work pool's job variables section) so that you don't risk having your build step and deployment specification get out of sync with hardcoded values.  

    !!! note Some steps require Prefect integrations
        Note that in the build step example above, we relied on the `prefect-docker` package; in cases that deal with external services, additional packages are often required and will be auto-installed for you.

    !!! tip "Pass output to downstream steps"
        Each deployment action can be composed of multiple steps. For example, if you wanted to build a Docker image tagged with the current commit hash, you could use the `run_shell_script` step and feed the output into the `build_docker_image` step:

        ```yaml
        build:
            - prefect.deployments.steps.run_shell_script:
                id: get-commit-hash
                script: git rev-parse --short HEAD
                stream_output: false
            - prefect_docker.deployments.steps.build_docker_image:
                requires: prefect-docker
                image_name: my-image
                image_tag: "{{ get-commit-hash.stdout }}"
                dockerfile: auto
        ```

        Note that the `id` field is used in the `run_shell_script` step so that its output can be referenced in the next step.

    ### The push action

    The push section is most critical for situations in which code is not stored on persistent filesystems or in version control.  In this scenario, code is often pushed and pulled from a Cloud storage bucket of some kind (e.g., S3, GCS, Azure Blobs, etc.).  The push section allows users to specify and customize the logic for pushing this code repository to arbitrary remote locations.

    For example, a user wishing to store their code in an S3 bucket and rely on default worker settings for its runtime environment could use the `s3` recipe:

    <div class="terminal">
    ```bash
    prefect init --recipe s3
    >> bucket: < insert bucket name here >
    ```
    </div>

    Inspecting our newly created `prefect.yaml` file we find that the `push` and `pull` sections have been templated out for us as follows:

    ```yaml
    push:
    - prefect_aws.deployments.steps.push_to_s3:
        id: push-code
        requires: prefect-aws>=0.3.0
        bucket: my-bucket
        folder: project-name
        credentials: null

    pull:
    - prefect_aws.deployments.steps.pull_from_s3:
        requires: prefect-aws>=0.3.0
        bucket: my-bucket
        folder: "{{ push-code.folder }}"
        credentials: null
    ```

    The bucket has been populated with our provided value (which also could have been provided with the `--field` flag); note that the `folder` property of the `push` step is a template - the `pull_from_s3` step outputs both a `bucket` value as well as a `folder` value that can be used to template downstream steps.  Doing this helps you keep your steps consistent across edits.

    As discussed above, if you are using [blocks](/concepts/blocks/), the credentials section can be templated with a block reference for secure and dynamic credentials access:

    ```yaml
    push:
    - prefect_aws.deployments.steps.push_to_s3:
        requires: prefect-aws>=0.3.0
        bucket: my-bucket
        folder: project-name
        credentials: "{{ prefect.blocks.aws-credentials.dev-credentials }}"
    ```

    Anytime you run `prefect deploy`, this `push` section will be executed upon successful completion of your `build` section. For more information on the mechanics of steps, [see below](#deployment-mechanics).

    ### The pull action

    The pull section is the most important section within the `prefect.yaml` file. It contains instructions for preparing your flows for a deployment run. These instructions will be executed each time a deployment created within this folder is run via a worker.

    There are three main types of steps that typically show up in a `pull` section:

    - `set_working_directory`: this step simply sets the working directory for the process prior to importing your flow
    - `git_clone`: this step clones the provided repository on the provided branch
    - `pull_from_{cloud}`: this step pulls the working directory from a Cloud storage location (e.g., S3)

    !!! tip "Use block and variable references"
        All [block and variable references](#templating-options) within your pull step will remain unresolved until runtime and will be pulled each time your deployment is run. This allows you to avoid storing sensitive information insecurely; it also allows you to manage certain types of configuration from the API and UI without having to rebuild your deployment every time.

    Below is an example of how to use an existing `GitHubCredentials` block to clone a private GitHub repository:

    ```yaml
    pull:
        - prefect.deployments.steps.git_clone:
            repository: https://github.com/org/repo.git
            credentials: "{{ prefect.blocks.github-credentials.my-credentials }}"
    ```

    Alternatively, you can specify a `BitBucketCredentials` or `GitLabCredentials` block to clone from Bitbucket or GitLab. In lieu of a credentials block, you can also provide a GitHub, GitLab, or Bitbucket token directly to the 'access_token` field. You can use a Secret block to do this securely:

    ```yaml
    pull:
        - prefect.deployments.steps.git_clone:
            repository: https://bitbucket.org/org/repo.git
            access_token: "{{ prefect.blocks.secret.bitbucket-token }}"
    ```

    ### Utility steps

    Utility steps can be used within a build, push, or pull action to assist in managing the deployment lifecycle:

    - `run_shell_script` allows for the execution of one or more shell commands in a subprocess, and returns the standard output and standard error of the script.
    This step is useful for scripts that require execution in a specific environment, or those which have specific input and output requirements.

    Here is an example of retrieving the short Git commit hash of the current repository to use as a Docker image tag:

    ```yaml
    build:
        - prefect.deployments.steps.run_shell_script:
            id: get-commit-hash
            script: git rev-parse --short HEAD
            stream_output: false
        - prefect_docker.deployments.steps.build_docker_image:
            requires: prefect-docker>=0.3.0
            image_name: my-image
            tag: "{{ get-commit-hash.stdout }}"
            dockerfile: auto
    ```

    !!! warning "Provided environment variables are not expanded by default"
        To expand environment variables in your shell script, set `expand_env_vars: true` in your `run_shell_script` step. For example:

        ```yaml
        - prefect.deployments.steps.run_shell_script:
            id: get-user
            script: echo $USER
            stream_output: true
            expand_env_vars: true
        ```

        Without `expand_env_vars: true`, the above step would return a literal string `$USER` instead of the current user.

    - `pip_install_requirements` installs dependencies from a `requirements.txt` file within a specified directory.

    Below is an example of installing dependencies from a `requirements.txt` file after cloning:

    ```yaml
    pull:
        - prefect.deployments.steps.git_clone:
            id: clone-step  # needed in order to be referenced in subsequent steps
            repository: https://github.com/org/repo.git
        - prefect.deployments.steps.pip_install_requirements:
            directory: {{ clone-step.directory }}  # `clone-step` is a user-provided `id` field
            requirements_file: requirements.txt
    ```

    Below is an example that retrieves an access token from a 3rd party Key Vault and uses it in a private clone step:

    ```yaml
    pull:
    - prefect.deployments.steps.run_shell_script:
        id: get-access-token
        script: az keyvault secret show --name <secret name> --vault-name <secret vault> --query "value" --output tsv
        stream_output: false
    - prefect.deployments.steps.git_clone:
        repository: https://bitbucket.org/samples/deployments.git
        branch: master
        access_token: "{{ get-access-token.stdout }}"
    ```

    You can also run custom steps by packaging them. In the example below, `retrieve_secrets` is a custom python module that has been packaged into the default working directory of a Docker image (which is /opt/prefect by default).
    `main` is the function entry point, which returns an access token (e.g. `return {"access_token": access_token}`) like the preceding example, but utilizing the Azure Python SDK for retrieval.

    ```yaml
    - retrieve_secrets.main:
        id: get-access-token
    - prefect.deployments.steps.git_clone:
        repository: https://bitbucket.org/samples/deployments.git
        branch: master
        access_token: '{{ get-access-token.access_token }}'
    ```

    ### Templating options

    Values that you place within your `prefect.yaml` file can reference dynamic values in several different ways:

    - **step outputs**: every step of both `build` and `push` produce named fields such as `image_name`; you can reference these fields within `prefect.yaml` and `prefect deploy` will populate them with each call.  References must be enclosed in double brackets and be of the form `"{{ field_name }}"`
    - **blocks**: [Prefect blocks](/concepts/blocks) can also be referenced with the special syntax `{{ prefect.blocks.block_type.block_slug }}`. It is highly recommended that you use block references for any sensitive information (such as a GitHub access token or any credentials) to avoid hardcoding these values in plaintext
    - **variables**: [Prefect variables](/concepts/variables) can also be referenced with the special syntax `{{ prefect.variables.variable_name }}`. Variables can be used to reference non-sensitive, reusable pieces of information such as a default image name or a default work pool name.
    - **environment variables**: you can also reference environment variables with the special syntax `{{ $MY_ENV_VAR }}`. This is especially useful for referencing environment variables that are set at runtime.

    As an example, consider the following `prefect.yaml` file:

    ```yaml
    build:
    - prefect_docker.deployments.steps.build_docker_image:
        id: build-image
        requires: prefect-docker>=0.3.0
        image_name: my-repo/my-image
        tag: my-tag
        dockerfile: auto
        push: true

    deployments:
    - # base metadata
        name: null
        version: "{{ build-image.tag }}"
        tags:
            - "{{ $my_deployment_tag }}"
            - "{{ prefect.variables.some_common_tag }}"
        description: null
        schedule: null

        # flow-specific fields
        entrypoint: null
        parameters: {}

        # infra-specific fields
        work_pool:
            name: "my-k8s-work-pool"
            work_queue_name: null
            job_variables:
                image: "{{ build-image.image }}"
                cluster_config: "{{ prefect.blocks.kubernetes-cluster-config.my-favorite-config }}"
    ```

    So long as our `build` steps produce fields called `image_name` and `tag`, every time we deploy a new version of our deployment, the `{{ build-image.image }}` variable will be dynamically populated with the relevant values.

    !!! note "Docker step"
        The most commonly used build step is [`prefect_docker.deployments.steps.build_docker_image`](/guides/deployment/docker/) which produces both the `image_name` and `tag` fields.

        For an example, [check out the deployments tutorial](/guides/deployment/docker/).

### Deployment Configurations

You can create multiple deployments from one or more python file that use `.deploy`. Similarly a `prefect.yaml` file can have multiple deployment configurations that control the behavior of created deployments.

These deployments can be managed independently of one another, allowing you to deploy the same flow with different configurations in the same codebase.

### Working with multiple deployments

=== ".deploy"

    To create multiple work pool-based deployments at once you can use the `deploy` function, which is analogous to the `serve` function.

    ```python
    from prefect import deploy, flow

    @flow(log_prints=True)
    def buy():
        print("Buying securities")
    
    
    if __name__ == "__main__":
        deploy(
            buy.to_deployment(name="dev-deploy", work_pool_name="my-dev-work-pool"),
            buy.to_deployment(name="prod-deploy", work_pool_name="my-prod-work-pool"),
            image="my-registry/my-image:dev",
            push=False,
        )
    ```

    Note that in the example above we created two deployments from the same flow, but with different work pools.
    Alternatively, we could have created two deployments from different flows.

    ```python
    from prefect import deploy, flow

    @flow(log_prints=True)
    def buy():
        print("Buying securities.")

    @flow(log_prints=True)
    def sell():
        print("Selling securities.")
    
    
    if __name__ == "__main__":
        deploy(
            buy.to_deployment(name="buy-deploy"),
            sell.to_deployment(name="sell-deploy"),
            work_pool_name="my-dev-work-pool"
            image="my-registry/my-image:dev",
            push=False,
        )
    ```

    In the example above the code for both flows gets baked into the same image.

    We can specify that one or more flows should be pulled from a remote location at runtime by using the `from_source` method.
    Here's an example of deploying two flows, one defined locally and one defined in a remote repository:

    ```python hl_lines="9-19"
    from prefect import deploy, flow


    @flow(log_prints=True)
    def local_flow():
        print("I'm a flow!")

    if __name__ == "__main__":
        deploy(
            local_flow.to_deployment(name="example-deploy-local-flow"),
            flow.from_source(
                source="https://github.com/org/repo.git",
                entrypoint="flows.py:my_flow",
            ).to_deployment(
                name="example-deploy-remote-flow",
            ),
            work_pool_name="my-work-pool",
            image="my-registry/my-image:dev",
        )
    ```

    You could pass any number of flows to the `deploy` function.
    This behavior is useful if using a monorepo approach to your workflows.

=== "prefect.yaml"

    Prefect supports multiple deployment declarations within the `prefect.yaml` file. This method of declaring multiple deployments allows the configuration for all deployments to be version controlled and deployed with a single command.

    New deployment declarations can be added to the `prefect.yaml` file by adding a new entry to the `deployments` list. Each deployment declaration must have a unique `name` field which is used to select deployment declarations when using the `prefect deploy` command.
    
    !!! warning
        When using a `prefect.yaml` file that is in another directory or differently named, remember that the value for 
        the deployment `entrypoint` must be relative to the root directory of the project.  

    For example, consider the following `prefect.yaml` file:

    ```yaml
    build: ...
    push: ...
    pull: ...

    deployments:
    - name: deployment-1
        entrypoint: flows/hello.py:my_flow
        parameters:
            number: 42,
            message: Don't panic!
        work_pool:
            name: my-process-work-pool
            work_queue_name: primary-queue

    - name: deployment-2
        entrypoint: flows/goodbye.py:my_other_flow
        work_pool:
            name: my-process-work-pool
            work_queue_name: secondary-queue

    - name: deployment-3
        entrypoint: flows/hello.py:yet_another_flow
        work_pool:
            name: my-docker-work-pool
            work_queue_name: tertiary-queue
    ```

    This file has three deployment declarations, each referencing a different flow. Each deployment declaration has a unique `name` field and can be deployed individually by using the `--name` flag when deploying.

    For example, to deploy `deployment-1` you would run:

    <div class="terminal">
    ```bash
    prefect deploy --name deployment-1
    ```
    </div>

    To deploy multiple deployments you can provide multiple `--name` flags:

    <div class="terminal">
    ```bash
    prefect deploy --name deployment-1 --name deployment-2
    ```
    </div>

    To deploy multiple deployments with the same name, you can prefix the deployment name with its flow name:

    <div class="terminal">
    ```bash
    prefect deploy --name my_flow/deployment-1 --name my_other_flow/deployment-1
    ```
    </div>

    To deploy all deployments you can use the `--all` flag:

    <div class="terminal">
    ```bash
    prefect deploy --all
    ```
    </div>

    To deploy deployments that match a pattern you can run:

    <div class="terminal">
    ```bash
    prefect deploy -n my-flow/* -n *dev/my-deployment -n dep*prod
    ```
    </div>

    The above command will deploy all deployments from the flow `my-flow`, all flows ending in `dev` with a deployment named `my-deployment`, and all deployments starting with `dep` and ending in `prod`.

    !!! note "CLI Options When Deploying Multiple Deployments"
        When deploying more than one deployment with a single `prefect deploy` command, any additional attributes provided via the CLI will be ignored.

        To provide overrides to a deployment via the CLI, you must deploy that deployment individually.

    ### Reusing configuration across deployments

    Because a `prefect.yaml` file is a standard YAML file, you can use [YAML aliases](https://yaml.org/spec/1.2.2/#71-alias-nodes) to reuse configuration across deployments.

    This functionality is useful when multiple deployments need to share the work pool configuration, deployment actions, or other configurations.

    You can declare a YAML alias by using the `&{alias_name}` syntax and insert that alias elsewhere in the file with the `*{alias_name}` syntax. When aliasing YAML maps, you can also override specific fields of the aliased map by using the `<<: *{alias_name}` syntax and adding additional fields below.

    We recommend adding a `definitions` section to your `prefect.yaml` file at the same level as the `deployments` section to store your aliases.

    For example, consider the following `prefect.yaml` file:

    ```yaml
    build: ...
    push: ...
    pull: ...

    definitions:
        work_pools:
            my_docker_work_pool: &my_docker_work_pool
                name: my-docker-work-pool
                work_queue_name: default
                job_variables:
                    image: "{{ build-image.image }}"
        schedules:
            every_ten_minutes: &every_10_minutes
                interval: 600
        actions:
            docker_build: &docker_build
                - prefect_docker.deployments.steps.build_docker_image: &docker_build_config
                    id: build-image
                    requires: prefect-docker>=0.3.0
                    image_name: my-example-image
                    tag: dev
                    dockerfile: auto
                    push: true

    deployments:
    - name: deployment-1
        entrypoint: flows/hello.py:my_flow
        schedule: *every_10_minutes
        parameters:
            number: 42,
            message: Don't panic!
        work_pool: *my_docker_work_pool
        build: *docker_build # Uses the full docker_build action with no overrides

    - name: deployment-2
        entrypoint: flows/goodbye.py:my_other_flow
        work_pool: *my_docker_work_pool
        build:
            - prefect_docker.deployments.steps.build_docker_image:
                <<: *docker_build_config # Uses the docker_build_config alias and overrides the dockerfile field
                dockerfile: Dockerfile.custom

    - name: deployment-3
        entrypoint: flows/hello.py:yet_another_flow
        schedule: *every_10_minutes
        work_pool:
            name: my-process-work-pool
            work_queue_name: primary-queue

    ```

    In the above example, we are using YAML aliases to reuse work pool, schedule, and build configuration across multiple deployments:

    - `deployment-1` and `deployment-2` are using the same work pool configuration
    - `deployment-1` and `deployment-3` are using the same schedule
    - `deployment-1` and `deployment-2` are using the same build deployment action, but `deployment-2` is overriding the `dockerfile` field to use a custom Dockerfile

    ## Deployment declaration reference

    ### Deployment fields

    Below are fields that can be added to each deployment declaration.

    | Property                                   | Description                                                                                                                                                                                                                                                                              |
    | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
    | `name`                                     | The name to give to the created deployment. Used with the `prefect deploy` command to create or update specific deployments.                                                                                                                                                             |
    | `version`                                  | An optional version for the deployment.                                                                                                                                                                                                                                                  |
    | `tags`                                     | A list of strings to assign to the deployment as tags.                                                                                                                                                                                                                                   |
    | <span class="no-wrap">`description`</span> | An optional description for the deployment.                                                                                                                                                                                                                                              |
    | `schedule`                                 | An optional [schedule](/concepts/schedules) to assign to the deployment. Fields for this section are documented in the [Schedule Fields](#schedule-fields) section.                                                                                                                      |
    | `triggers`                                  | An optional array of [triggers](/concepts/deployments/#create-a-flow-run-with-an-event-trigger) to assign to the deployment |
    | `entrypoint`                               | Required path to the `.py` file containing the flow you want to deploy (relative to the root directory of your development folder) combined with the name of the flow function. Should be in the format `path/to/file.py:flow_function_name`. |
    | `parameters`                               | Optional default values to provide for the parameters of the deployed flow. Should be an object with key/value pairs.                                                                                                                                                                    |
    | <span class="no-wrap">`enforce_parameter_schema`</span>                              | Boolean flag that determines whether the API should validate the parameters passed to a flow run against the parameter schema generated for the deployed flow.                                                                                                                                                                    |
    | `work_pool`                                | Information on where to schedule flow runs for the deployment. Fields for this section are documented in the [Work Pool Fields](#work-pool-fields) section.                                                                                                                              |

    ### Schedule fields

    Below are fields that can be added to a deployment declaration's `schedule` section.

    | Property                                   | Description                                                                                                                                                                                                            |
    | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
    | `interval`                                 | Number of seconds indicating the time between flow runs. Cannot be used in conjunction with `cron` or `rrule`.                                                                                                         |
    | <span class="no-wrap">`anchor_date`</span> | Datetime string indicating the starting or "anchor" date to begin the schedule. If no `anchor_date` is supplied, the current UTC time is used. Can only be used with `interval`.                                       |
    | `timezone`                                 | String name of a time zone, used to enforce localization behaviors like DST boundaries. See the [IANA Time Zone Database](https://www.iana.org/time-zones) for valid time zones.                                       |
    | `cron`                                     | A valid cron string. Cannot be used in conjunction with `interval` or `rrule`.                                                                                                                                         |
    | `day_or`                                   | Boolean indicating how croniter handles day and day_of_week entries. Must be used with `cron`. Defaults to `True`.                                                                                                     |
    | `rrule`                                    | String representation of an RRule schedule. See the [`rrulestr` examples](https://dateutil.readthedocs.io/en/stable/rrule.html#rrulestr-examples) for syntax. Cannot be used in conjunction with `interval` or `cron`. |

    For more information about schedules, see the [Schedules](/concepts/schedules/#creating-schedules-through-a-deployment-yaml-files-schedule-section) concept doc.

    ### Work pool fields

    Below are fields that can be added to a deployment declaration's `work_pool` section.

    | Property                                       | Description                                                                                                                                                                                               |
    | ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
    | `name`                                         | The name of the work pool to schedule flow runs in for the deployment.                                                                                                                                    |
    | <span class="no-wrap">`work_queue_name`</span> | The name of the work queue within the specified work pool to schedule flow runs in for the deployment. If not provided, the default queue for the specified work pool will be used.                       |
    | `job_variables`                                | Values used to override the default values in the specified work pool's [base job template](/concepts/work-pools/#base-job-template). Maps directly to a created deployments `infra_overrides` attribute. |

    ## Deployment mechanics

    Anytime you run `prefect deploy` in a directory that contains a `prefect.yaml` file, the following actions are taken in order:

    - The `prefect.yaml` file is loaded. First, the `build` section is loaded and all variable and block references are resolved. The steps are then run in the order provided.
    - Next, the `push` section is loaded and all variable and block references are resolved; the steps within this section are then run in the order provided
    - Next, the `pull` section is templated with any step outputs but _is not run_.  Note that block references are _not_ hydrated for security purposes - block references are always resolved at runtime
    - Next, all variable and block references are resolved with the deployment declaration.  All flags provided via the `prefect deploy` CLI are then overlaid on the values loaded from the file.
    - The final step occurs when the fully realized deployment specification is registered with the Prefect API

    !!! tip "Deployment Instruction Overrides"
        The `build`, `push`, and `pull` sections in deployment definitions take precedence over the corresponding sections above them in `prefect.yaml`.

    Each time a step is run, the following actions are taken in order:

    - The step's inputs and block / variable references are resolved (see [the templating documentation above](#templating-options) for more details).
    - The step's function is imported; if it cannot be found, the special `requires` keyword is used to install the necessary packages
    - The step's function is called with the resolved inputs.
    - The step's output is returned and used to resolve inputs for subsequent steps.

## Next steps

Now that you are familiar with creating deployments, you may want to explore [push work pools](/guides/deployment/kubernetes) or [Kubernetes work pools](/guides/deployment/kubernetes).
