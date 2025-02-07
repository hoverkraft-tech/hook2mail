import contextlib
import dagger
import platform
import sys
from dagger import Doc, Ignore, dag, function, object_type
from typing import Annotated

IGNORE_LIST = [
    ".dagger",
    ".dockerignore",
    ".envrc",
    ".git*",
    ".llms",
    ".venv",
    ".vscode",
    "docker-compose*",
    "Dockerfile",
    "k8s",
]

@contextlib.asynccontextmanager
async def managed_service(svc: dagger.Service):
    """Start and stop a service."""
    yield await svc.start()
    await svc.stop()

@object_type
class Hook2Mail:

    @function
    async def test_405(
        self,
        source: Annotated[dagger.Directory, Ignore(IGNORE_LIST)],
        platform: dagger.Platform
    ) -> str:
        """when calling /webhook using GET ethod i should see a 405"""
        ctr = (
            self.build_env(source, platform)
            .with_exposed_port(8080)
            .as_service(use_entrypoint=True)
        )

        async with managed_service(ctr) as api:
            # test: http request "GET /webhook" that will send a 405 ok error
            res = (
                dag.container()
                .from_("curlimages/curl")
                .with_service_binding("api", api)
                .with_exec([
                    "curl", "-qsS", "-o", "/dev/null", "-X", "GET",
                    "-w", "'%{response_code}'",
                    f"http://api:8080/webhook"
                ])
            )
            stdout = await res.stdout()
            stderr = await res.stderr()
            stdout = int(stdout.strip("'"))
            assert stdout == 405, (f"Expected 405, got stdout={stdout} stderr={stderr}")
            return "ok"

    @function
    async def test_200(
        self,
        source: Annotated[dagger.Directory, Ignore(IGNORE_LIST)],
        platform: dagger.Platform
    ) -> str:
        """when sending a valid payload to the webhook we must receive a 200 code"""

        mailhog = (
            dag.container(platform=platform)
            .from_("mailhog/mailhog:latest")
            .with_exposed_port(1025)
            .with_exposed_port(8025)
            .as_service()
        )

        ctr = (
            self.build_env(source, platform)
            .with_exposed_port(8080)
            .with_service_binding("mailhog", mailhog)
            .with_env_variable("SMTP_HOST", "mailhog")
            .with_env_variable("SMTP_PORT", "1025")
            .with_env_variable("USE_STARTTLS", "false")
            .with_env_variable("USE_LOGIN", "false")
            .as_service(use_entrypoint=True)
        )

        async with managed_service(mailhog) as mailhog, managed_service(ctr) as api:
            # test: http request "POST /webhook" that will send a 200 code
            res = (
                dag.container()
                .from_("curlimages/curl")
                .with_service_binding("api", api)
                .with_mounted_directory("/code", source)
                .with_exec([
                    "curl", "-qsS", "-o", "/dev/null", "-X", "POST",
                    "-H", "Content-Type: application/json; charset=utf-8",
                    "-d", "@/code/tests/simple.json",
                    "-w", "'%{response_code}'",
                    f"http://api:8080/webhook"
                ])
            )
            stdout = await res.stdout()
            stderr = await res.stderr()
            stdout = int(stdout.strip("'"))
            assert stdout == 200, (f"Expected 200, got stdout={stdout} stderr={stderr}")
            return "ok"

    @function
    async def build(
        self,
        source: Annotated[dagger.Directory, Ignore(IGNORE_LIST)],
        registry: str,
        repository: str,
        username: str,
        password: dagger.Secret,
        tag: str,
        platforms: list[str] =  []
    ) -> str:
        """ build our OCI images """

        _platforms = []
        if platforms == []:
            _p = self.get_default_platform()
            _platforms.append(dagger.Platform(_p))
        else:
            _platforms = list(
                map(lambda p: dagger.Platform(p), platforms)
            )

        p = await self.build_oci(source, registry, repository, username, password, tag, _platforms)
        return p

    async def build_oci(
        self,
        source: Annotated[dagger.Directory, Ignore(IGNORE_LIST)],
        registry: str,
        repository: str,
        username: str,
        password: dagger.Secret,
        tag: str,
        platforms: list[dagger.Platform]
    ) -> str:
        """Build an publish multi-platform image"""

        oci_name = ("%s/%s:%s" % (registry, repository, tag))
        print("OCI_IMAGE: %s" % oci_name)

        platform_variants = []
        for p in platforms:
            ctr = self.build_env(source, p)
            platform_variants.append(ctr)

        image_digest = (
            dag.container()
            .with_registry_auth(registry, username, password)
            .publish(oci_name, platform_variants=platform_variants)
        )
        return await image_digest

    @function
    def build_env(
        self,
        source: Annotated[dagger.Directory, Ignore(IGNORE_LIST)],
        platform: dagger.Platform
    ) -> dagger.Container:
        """build-env : build container image"""


        cache = dag.cache_volume("pycache")
        built = (
            dag.container(platform=platform)
                .from_("python:3.13-slim")
                .with_directory("/app", source)
                .with_mounted_cache("/root/.cache", cache)
                .with_env_variable("PYTHONUNBUFFERED", "1")
                .with_env_variable("POETRY_NO_INTERACTION", "1")
                .with_env_variable("POETRY_VIRTUALENVS_IN_PROJECT", "1")
                .with_env_variable("POETRY_VIRTUALENVS_CREATE", "1")
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
                .with_exec(["pip", "install", "--upgrade", "poetry"])
                .with_exec(["poetry", "install", "--no-root"])
                .with_entrypoint(["poetry", "run", "python", "hook2mail.py"])
        )
        return built

    def get_default_platform(self) -> str:
        """Determine the default platform if none is provided."""
        os_name = sys.platform
        arch = platform.machine()

        # Normalize architecture names
        arch_map = {
            "x86_64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
            "i386": "386",
            "armv7l": "arm/v7",
        }

        normalized_arch = arch_map.get(arch, "amd64")  # Default to amd64
        detected_platform = f"linux/{normalized_arch}"

        print(f"Detected host platform: {detected_platform}")
        return detected_platform
