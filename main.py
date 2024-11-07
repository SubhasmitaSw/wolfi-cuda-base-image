import sys
import asyncio
import dagger
import os

# Define configurations
# OS_VERSIONS = ["jammy", "focal"] #ubuntu based images 
OS_VERSIONS = ["wolfi"] # wolfi based images
CUDA_VERSIONS = ["12.4.1"]
CONTAINER_TYPES = ["", "pytorch", "tensorflow=2.15.0"]
PYTHON_VERSIONS = ["3.11"]

async def build_and_publish_image(client, os_version, cuda_version, container_type, python_version, repository, username, password):

     # Determine image reference
    container_type_tag = "base" if container_type == "" else "tensorflow" if "tensorflow" in container_type else container_type
    img_ref = f"{os_version}_python_{python_version}_cuda_{cuda_version}_{container_type_tag}"

    # # Set up the base container with micromamba 
    # base_image = f"ghcr.io/mamba-org/micromamba:{os_version}-cuda-{cuda_version}"

    # Set up the base container with wolfi 
    base_image = f"cgr.dev/chainguard/wolfi-base:cuda-{cuda_version}"


    secret = client.set_secret("password", password)
    container = (
        client.container()
        .from_(base_image)
        .with_user("root")
        .with_workdir("/app")
        # Install Micromamba
        .with_exec(["/bin/sh", "-c", "apk add --no-cache curl && curl -Ls https://micro.mamba.pm/install.sh | bash"])
        # Install packages using Micromamba
        .with_exec(["/bin/sh", "-c", f"micromamba install -y -n base -c conda-forge {container_type} python={python_version} && micromamba clean --all --yes && micromamba list"])
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