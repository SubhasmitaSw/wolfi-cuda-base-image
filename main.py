import sys
import asyncio
import dagger
import os

# Define configurations
OS_VERSIONS = ["jammy", "focal"]
CUDA_VERSIONS = ["12.4.1", "11.8.0"]
CONTAINER_TYPES = ["", "pytorch", "tensorflow=2.15.0"]
PYTHON_VERSIONS = ["3.10", "3.11"]


async def build_image(client, os_version, cuda_version, container_type, python_version, username, password):
    # Determine image reference
    container_type_tag = "base" if container_type == "" else "tensorflow" if "tensorflow" in container_type else container_type
    img_ref = f"civo_{os_version}_python_{python_version}_cuda_{cuda_version}_{container_type_tag}"

    # Set up Docker container
    base_image = f"ghcr.io/mamba-org/micromamba:{os_version}-cuda-{cuda_version}"
    container = (
        client.container()
        .from_(base_image)
        .with_user("root")
        .with_workdir("/app")
        .with_exec(["/bin/sh", "-c", f"micromamba install -y -n base -c conda-forge {container_type} python={python_version} && micromamba clean --all --yes && micromamba list"])
        .with_env_variable("MAMBA_DOCKERFILE_ACTIVATE", "1")
        .with_registry_auth(address=f"https://ghcr.io", secret=client.set_secret(name="password", plaintext=password), username=username)
    )

    # Publish Docker image
    await container.publish(f"{img_ref}")

    # Display build logs
    try:
        async for line in container.logs():
            print(line)
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    return True


async def main():
    # Get authentication details
    username = os.environ.get("username")
    password = os.environ.get("password")

    if not username or not password:
        print("Environment variables 'username' and 'password' are required.")
        return

    async with dagger.Connection(dagger.Config(log_output=sys.stderr)) as client:
        # Build images for all combinations of configurations
        tasks = [
            build_image(client, os_version, cuda_version, container_type, python_version, username, password)
            for os_version in OS_VERSIONS
            for cuda_version in CUDA_VERSIONS
            for container_type in CONTAINER_TYPES
            for python_version in PYTHON_VERSIONS
        ]

        # Execute tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # Display errors, if any
        for os_version, cuda_version, container_type, python_version, success in zip(
                [os_version for os_version in OS_VERSIONS for _ in range(len(CUDA_VERSIONS) * len(CONTAINER_TYPES) * len(PYTHON_VERSIONS))],
                [cuda_version for _ in range(len(OS_VERSIONS)) for cuda_version in CUDA_VERSIONS for _ in range(len(CONTAINER_TYPES) * len(PYTHON_VERSIONS))],
                [container_type for _ in range(len(OS_VERSIONS) * len(CUDA_VERSIONS)) for container_type in CONTAINER_TYPES for _ in range(len(PYTHON_VERSIONS))],
                [python_version for _ in range(len(OS_VERSIONS) * len(CUDA_VERSIONS) * len(CONTAINER_TYPES)) for python_version in PYTHON_VERSIONS],
                results):
            if not success:
                print(f"Error encountered during build for {os_version}, {cuda_version}, {container_type}, {python_version}")


if __name__ == "__main__":
    asyncio.run(main())
