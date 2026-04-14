from pathlib import Path

from django.conf import settings

from .base import BasePrinterAdapter


class PdfFilePrinterAdapter(BasePrinterAdapter):
    driver_type = "pdf_file"

    def dispatch(self, printer, documents, print_job):
        output_dir = Path(getattr(settings, "PRINT_OUTPUT_DIR", settings.BASE_DIR / "print_output"))
        output_dir.mkdir(parents=True, exist_ok=True)

        files = []

        for index, document in enumerate(documents, start=1):
            filename = output_dir / f"print_job_{print_job.id}_doc_{index}.pdf.txt"
            filename.write_text(str(document), encoding="utf-8")
            files.append(str(filename))

        return {
            "mode": self.driver_type,
            "files": files,
            "documents_generated": len(files),
            "message": f"{len(files)} PDF placeholder file(s) generated.",
        }