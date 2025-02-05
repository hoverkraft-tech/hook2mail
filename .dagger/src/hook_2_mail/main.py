import logging
import os
import uuid
import dagger
from dagger import dag, function, object_type
from dagger.log import configure_logging

configure_logging(logging.INFO)

@object_type
class Hook2Mail:

    @function
    async def build_oci(self, registry: str, repository: str, tag: str) -> str:
        """Build an publish multi-platform image"""
        platforms = [
            dagger.Platform("linux/amd64"),
            dagger.Platform("linux/arm64"),
        ]

        oci_name = ("%s/%s:%s" % (registry, repository, tag))
        print("OCI_IMAGE: %s" % oci_name)
        return ""

    @function
    def build_env(self, source: dagger.Directory, platform: dagger.Platform) -> dagger.Container:
        """build-env : build docker image"""
        pip_cache = dag.cache_volume("pip")
        built = (
            dag.container()
                .from_("python:3.9-slim")
                .with_directory("/app", source)
                .with_mounted_cache("/root/.cache/pip", pip_cache)
                .with_env_variable("PYTHONUNBUFFERED", "1")
                .with_env_variable("PORT", "8080")
                .with_env_variable("SMTP_HOST", "localhost")
                .with_env_variable("SMTP_PORT", "25")
                .with_env_variable("USE_STARTTLS", "true")
                .with_env_variable("USE_LOGIN", "false")
                .with_env_variable("SMTP_USER", "")
                .with_env_variable("SMTP_PASSWORD", "")
                .with_env_variable("EMAIL_FROM", "no-reply@example.com")
                .with_env_variable("EMAIL_TO", "no-reply@example.com")
                .with_workdir("/app")
                .with_exec(["pip", "install", "--upgrade", "pip"])
                .with_exec(["pip", "install", "-r", "requirements.txt"])
                .with_entrypoint(["python", "hook2mail.py"])
        )
        return built
