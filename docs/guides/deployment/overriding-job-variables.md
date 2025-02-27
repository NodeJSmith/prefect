---
description: Learn how to override job variables on a work pool for a given deployment.
tags:
    - deployments
    - work pools
    - job variables
    - environment variables
search:
  boost: 2
---

# Deeper Dive: Overriding Work Pool Job Variables

As described in the [Deploying Flows to Work Pools and Workers](/guides/prefect-deploy/) guide, there are two ways to deploy flows to work pools: using a `prefect.yaml` file or using the `.deploy()` method.

**In both cases, you can override job variables on a work pool for a given deployment.**

While exactly _which_ job variables are available to be overridden depend on the type of work pool you're using at a given time, this guide will explore some common patterns for overriding job variables in both deployment methods.

## Background
First of all, what are _"job variables"_?

Job variables are infrastructure related values that are configurable on a work pool, which may be relevant to how your flow run executes on your infrastructure.

<hr>

Let's use `env` - the only job variable that is configurable for all work pool types - as an example.

When you create or edit a work pool, you can specify a set of environment variables that will be set in the runtime environment of the flow run.

For example, you might want a certain deployment to have the following environment variables available:
```json
{
  "EXECUTION_ENV": "staging",
  "MY_NOT_SO_SECRET_CONFIG": "plumbus",
}
```

Rather than hardcoding these values into your work pool in the UI and making them available to all deployments associated with that work pool, you can override these values on a _per-deployment basis_.

Let's look at how to do that.

## How to override job variables
Say we have the following repo structure:
```
» tree
.
├── README.md
├── requirements.txt
├── demo_project
│   ├── daily_flow.py
```

... and we have some `demo_flow.py` file like this:

```python
import os
from prefect import flow, task

@task
def do_something_important(not_so_secret_value: str) -> None:
    print(f"Doing something important with {not_so_secret_value}!")

@flow(log_prints=True)
def some_work():
    environment = os.environ.get("EXECUTION_ENVIRONMENT", "local")
    
    print(f"Coming to you live from {environment}!")
    
    not_so_secret_value = os.environ.get("MY_NOT_SO_SECRET_CONFIG")
    
    if not_so_secret_value is None:
        raise ValueError("You forgot to set MY_NOT_SO_SECRET_CONFIG!")

    do_something_important(not_so_secret_value)
```
### Using a `prefect.yaml` file
In this case, let's also say we have the following deployment definition in a `prefect.yaml` file at the root of our repository:
```yaml
deployments:
- name: demo-deployment
  entrypoint: demo_project/demo_flow.py:some_work
  work_pool:
    name: local
  schedule: null
```

!!! note
    While not the focus of this guide, note that this deployment definition uses a default "global" `pull` step, because one is not explicitly defined on the deployment. For reference, here's what that would look like at the top of the `prefect.yaml` file:
    ```yaml
    pull:
    - prefect.deployments.steps.git_clone: &clone_repo
        repository: https://github.com/some-user/prefect-monorepo
        branch: main
    ```

#### Hard-coded job variables
To provide the `EXECUTION_ENVIRONMENT` and `MY_NOT_SO_SECRET_CONFIG` environment variables to this deployment, we can add a `job_variables` section to our deployment definition in the `prefect.yaml` file:

```yaml
deployments:
- name: demo-deployment
  entrypoint: demo_project/demo_flow.py:some_work
  work_pool:
    name: local
    job_variables:
        env:
            EXECUTION_ENVIRONMENT: staging
            MY_NOT_SO_SECRET_CONFIG: plumbus
  schedule: null
```

... and then run `prefect deploy -n demo-deployment` to deploy the flow with these job variables.

We should then be able to see the job variables in the `Configuration` tab of the deployment in the UI:

![Job variables in the UI](/img/guides/job-variables.png)

#### Using existing environment variables
If you want to use environment variables that are already set in your local environment, you can template these in the `prefect.yaml` file using the `{{ $ENV_VAR_NAME }}` syntax:

```yaml
deployments:
- name: demo-deployment
  entrypoint: demo_project/demo_flow.py:some_work
  work_pool:
    name: local
    job_variables:
        env:
            EXECUTION_ENVIRONMENT: "{{ $EXECUTION_ENVIRONMENT }}"
            MY_NOT_SO_SECRET_CONFIG: "{{ $MY_NOT_SO_SECRET_CONFIG }}"
  schedule: null
```

!!! note
    This assumes that the machine where `prefect deploy` is run would have these environment variables set.

    <div class="terminal">
    ```bash
    export EXECUTION_ENVIRONMENT=staging
    export MY_NOT_SO_SECRET_CONFIG=plumbus
    ```
    </div>

As before, run `prefect deploy -n demo-deployment` to deploy the flow with these job variables, and you should see them in the UI under the `Configuration` tab.

### Using the `.deploy()` method
If you're using the `.deploy()` method to deploy your flow, the process is similar, but instead of having your `prefect.yaml` file define the job variables, you can pass them as a dictionary to the `job_variables` argument of the `.deploy()` method.

We could add the following block to our `demo_project/daily_flow.py` file from the setup section:
```python
if __name__ == "__main__":
    flow.from_source(
        source="https://github.com/zzstoatzz/prefect-monorepo.git",
        entrypoint="src/demo_project/demo_flow.py:some_work"
    ).deploy(
        name="demo-deployment",
        work_pool_name="local", # can only .deploy() to a local work pool in prefect>=2.15.1
        job_variables={
            "env": {
                "EXECUTION_ENVIRONMENT": os.environ.get("EXECUTION_ENVIRONMENT", "local"),
                "MY_NOT_SO_SECRET_CONFIG": os.environ.get("MY_NOT_SO_SECRET_CONFIG")
            }
        }
    )
```

!!! note
    The above example works assuming a couple things:
    - the machine where this script is run would have these environment variables set.
    <div class="terminal">
    ```bash
    export EXECUTION_ENVIRONMENT=staging
    export MY_NOT_SO_SECRET_CONFIG=plumbus
    ```
    </div>

    - `demo_project/daily_flow.py` _already exists_ in the repository at the specified path

Running this script with something like:
<div class="terminal">
```bash
python demo_project/daily_flow.py
```
</div>
... will deploy the flow with the specified job variables, which should then be visible in the UI under the `Configuration` tab.

![Job variables in the UI](/img/guides/job-variables.png)