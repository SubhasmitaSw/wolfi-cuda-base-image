import sys
import asyncio
import dagger
import os

# Define configurations
OS_VERSIONS = ["jammy"]
CUDA_VERSIONS = ["12.4.1"]
CONTAINER_TYPES = ["", "pytorch", "tensorflow=2.15.0"]
PYTHON_VERSIONS = ["3.10", "3.11"]

async def build_and_publish_image(client, os_version, cuda_version, container_type, python_version, repository, username, password):

     # Determine image reference
    container_type_tag = "base" if container_type == "" else "tensorflow" if "tensorflow" in container_type else container_type
    img_ref = f"civo_{os_version}_python_{python_version}_cuda_{cuda_version}_{container_type_tag}"

    # Set up the base container
    base_image = f"ghcr.io/mamba-org/micromamba:{os_version}-cuda-{cuda_version}"

    secret = client.set_secret("password", password)
    container = (
        client.container()
        .from_(base_image)
        .with_user("root")
        .with_workdir("/app")
        .with_exec(["/bin/sh", "-c", f"micromamba install -y -n base -c conda-forge {container_type} python={python_version} && micromamba clean --all --yes && micromamba list"])
        .with_env_variable("MAMBA_DOCKERFILE_ACTIVATE", "1")
        # add LABEL to the dockerfile to automatically associate the image with the repository on container registry
        .with_label("org.opencontainers.image.source", f"https://github.com/{username}/{repository}")
        .with_registry_auth(address="ghcr.io", username=username, secret=secret)
    )

    await container.publish(f"ghcr.io/{username}/{img_ref}")


async def main():
    repository = "wolfi-cuda-base-image"
    username = os.environ.get("username")
    password = os.environ.get("password")

    if not username or not password:
        print("Environment variables 'username' and 'password' are required.")
        return
    
    
    async with dagger.Connection(dagger.Config(log_output=sys.stderr)) as client:
        tasks = [
                build_and_publish_image(client, os_version, cuda_version, container_type, python_version, repository, username, password)
                for os_version in OS_VERSIONS
                for cuda_version in CUDA_VERSIONS
                for container_type in CONTAINER_TYPES
                for python_version in PYTHON_VERSIONS
            ]

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

    print("Images built and published successfully!")