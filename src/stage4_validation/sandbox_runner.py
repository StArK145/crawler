import docker
import os
import time
import shutil
from pathlib import Path
from typing import Tuple, Optional

class TypeCheckException(Exception):
    """Raised when the framework's type-checker (tsc/vue-tsc) fails."""
    def __init__(self, errors: str):
        self.errors = errors
        super().__init__(f"Type-check failed:\n{errors}")

class SandboxEnvironment:
    """
    Orchestrates an ephemeral Docker container for high-speed frontend validation.
    Uses a pre-warmed pnpm store to ensure sub-2s dependency installation.
    """

    def __init__(self, pnpm_store_path: str = "/tmp/pnpm-store"):
        self.client = docker.from_env()
        self.pnpm_store_path = Path(pnpm_store_path).absolute()
        # Ensure the host store exists or is initialized
        self.pnpm_store_path.mkdir(parents=True, exist_ok=True)

    def _get_dockerfile(self, framework: str) -> str:
        """
        Generates a framework-specific Dockerfile utilizing node:22-alpine.
        """
        # Base image with pnpm installed
        dockerfile = (
            "FROM node:22-alpine\n"
            "RUN corepack enable && corepack prepare pnpm@latest --activate\n"
            "WORKDIR /app\n"
        )

        # Framework-specific global tools
        if framework == "vue":
            dockerfile += "RUN pnpm add -g vue-tsc typescript\n"
        elif framework == "angular":
            dockerfile += "RUN pnpm add -g @angular/cli\n"
        else: # react/next
            dockerfile += "RUN pnpm add -g typescript\n"

        return dockerfile

    async def run_build_and_start(self, project_path: str, framework: str) -> Tuple[str, Any]:
        """
        Executes the install -> typecheck -> start pipeline in an ephemeral container.
        """
        project_path = Path(project_path).absolute()

        # 1. Build/Load ephemeral image
        image_tag = f"sandbox-{framework}:latest"
        # In a real implementation, we would cache this image
        self.client.images.build(
            path=".",
            dockerfile=self.get_dockerfile_path(framework),
            tag=image_tag
        )

        # 2. Run container with read-only pnpm store mount
        container = self.client.containers.run(
            image=image_tag,
            command="sh -c 'pnpm install --offline --frozen-lockfile && pnpm run typecheck && pnpm run dev'",
            volumes={
                str(project_path): {'bind': '/app', 'mode': 'rw'},
                str(self.pnpm_store_path): {'bind': '/root/.local/share/pnpm/store', 'mode': 'ro'}
            },
            detach=True,
            ports={'5173/tcp': 5173, '3000/tcp': 3000},
            working_dir="/app"
        )

        # 3. Monitor logs for typecheck failure
        # We poll logs until 'pnpm run dev' starts or failure occurs
        start_time = time.time()
        while time.time() - start_time < 15: # 15s timeout
            logs = container.logs().decode('utf-8')
            if "error TS" in logs or "failed" in logs.lower():
                container.stop()
                container.remove()
                raise TypeCheckException(logs)
            if "Local: http" in logs:
                # Success: Server is booting
                url = "http://localhost:5173" if framework != "next" else "http://localhost:3000"
                return url, container
            time.sleep(0.5)

        # Timeout
        container.stop()
        container.remove()
        raise TimeoutError("Sandbox failed to boot within 15 seconds")

    def get_dockerfile_path(self, framework: str) -> str:
        """Temporary helper to write dockerfile to disk for the build context."""
        df_path = Path(f"Dockerfile.{framework}")
        df_path.write_text(self._get_dockerfile(framework))
        return str(df_path)
