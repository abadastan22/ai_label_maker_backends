from pathlib import Path

from django.conf import settings

from .base import BasePrinterAdapter


class MockFilePrinterAdapter(BasePrinterAdapter):
    driver_type = "mock_file"

    def dispatch(self, printer, documents, print_job):
        output_dir = Path(getattr(settings, "PRINT_OUTPUT_DIR", settings.BASE_DIR / "print_output"))
        output_dir.mkdir(parents=True, exist_ok=True)

        written_files = []

        for index, document in enumerate(documents, start=1):
            suffix = ".txt"
            if isinstance(document, str) and document.lstrip().startswith("<"):
                suffix = ".html"
            elif isinstance(document, (bytes, bytearray)):
                suffix = ".bin"

            filename = output_dir / f"print_job_{print_job.id}_doc_{index}{suffix}"

            if isinstance(document, str):
                filename.write_text(document, encoding="utf-8")
            else:
                filename.write_bytes(document)

            written_files.append(str(filename))

        return {
            "mode": self.driver_type,
            "files": written_files,
            "documents_written": len(written_files),
            "message": f"{len(written_files)} document(s) written to disk.",
        }