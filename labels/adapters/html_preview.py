from pathlib import Path

from django.conf import settings

from .base import BasePrinterAdapter


class HtmlPreviewPrinterAdapter(BasePrinterAdapter):
    driver_type = "html_preview"

    def dispatch(self, printer, documents, print_job):
        output_dir = Path(getattr(settings, "PRINT_OUTPUT_DIR", settings.BASE_DIR / "print_output"))
        output_dir.mkdir(parents=True, exist_ok=True)

        preview_files = []

        for index, document in enumerate(documents, start=1):
            filename = output_dir / f"preview_job_{print_job.id}_doc_{index}.html"
            filename.write_text(str(document), encoding="utf-8")
            preview_files.append(str(filename))

        return {
            "mode": self.driver_type,
            "preview_files": preview_files,
            "documents_prepared": len(preview_files),
            "message": f"{len(preview_files)} HTML preview file(s) prepared.",
        }