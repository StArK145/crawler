import os
import re
import shutil
import zipfile
import json
from pathlib import Path
from typing import List, Dict, Any

class ProjectExporter:
    """
    Final delivery engine that scrubs internal telemetry, generates mock services,
    and packages the project for delivery.
    """

    def __init__(self):
        # Regex to find and remove data-ir-id="..." attributes
        self.ir_id_regex = re.compile(r'\s*data-ir-id="[^"]*"')

    def scrub_ir_metadata(self, project_path: str):
        """
        Traverses the generated project and strips all internal telemetry tags.
        """
        project_root = Path(project_path)

        # We only scrub source files that might contain the attributes
        target_extensions = {'.tsx', '.jsx', '.vue', '.html', '.ts', '.js'}

        for file_path in project_root.rglob('*'):
            if file_path.suffix in target_extensions:
                content = file_path.read_text(encoding='utf-8')
                scrubbed_content = self.ir_id_regex.sub('', content)

                if scrubbed_content != content:
                    file_path.write_text(scrubbed_content, encoding='utf-8')

    def generate_mock_api(self, har_data: Dict[str, Any], project_path: str):
        """
        Parses Sanitized HAR data and generates MSW (Mock Service Worker) handlers.
        Extracts application/json responses to create local mock endpoints.
        """
        project_root = Path(project_path)
        handlers = []

        # Extract entries from HAR
        entries = har_data.get('log', {}).get('entries', [])

        for entry in entries:
            request = entry.get('request', {})
            response = entry.get('response', {})

            # Filter for GET requests returning JSON
            if request.get('method') == 'GET' and 'application/json' in response.get('content', {}).get('mimeType', ''):
                url = request.get('url')
                # In a real implementation, we would sanitize the URL to a relative path
                endpoint = url.split('?') [0]

                try:
                    payload = json.loads(response.get('content', {}).get('text', '{}'))

                    # Generate MSW handler string
                    handler_str = (
                        f"rest.get('{endpoint}', (req, res, ctx) => "
                        f"res(ctx.status(200), ctx.json({json.dumps(payload)})))"
                    )
                    handlers.append(handler_str)
                except json.JSONDecodeError:
                    continue

        # Write to handlers.ts
        mock_dir = project_root / "src" / "mocks"
        mock_dir.mkdir(parents=True, exist_ok=True)

        handlers_file = mock_dir / "handlers.ts"

        full_content = (
            "import { rest } from 'msw';\n\n"
            "export const handlers = [\n"
            f"  {',\n  '.join(handlers)}\n"
            "];"
        )

        handlers_file.write_text(full_content, encoding='utf-8')

    def package_zip(self, project_path: str, output_dir: str) -> str:
        """
        Compresses the project into a .zip archive, excluding build artifacts and deps.
        """
        project_root = Path(project_path)
        out_root = Path(output_dir)
        out_root.mkdir(parents=True, exist_ok=True)

        zip_filename = f"project_export_{int(os.path.getmtime(project_root))}.zip"
        zip_path = out_root / zip_filename

        exclude_dirs = {'node_modules', '.git', '.next', 'dist', '.vue-tsc'}

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in project_root.rglob('*'):
                # Check if any part of the path is in exclude_dirs
                if any(part in exclude_dirs for part in file_path.relative_to(project_root).parts):
                    continue

                if file_path.is_file():
                    zipf.write(file_path, file_path.relative_to(project_root))

        return str(zip_path)
