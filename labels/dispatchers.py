import os
import socket
from pathlib import Path

from django.conf import settings

from .exceptions import PrinterDispatchError


class BasePrinterDispatcher:
    def dispatch(self, printer, rendered_documents, print_job):
        raise NotImplementedError("Dispatchers must implement dispatch().")


class MockFilePrinterDispatcher(BasePrinterDispatcher):
    """
    Writes rendered label HTML into local files for testing.
    Good for early backend/frontend integration before real printer hardware.
    """

    def dispatch(self, printer, rendered_documents, print_job):
        output_dir = Path(getattr(settings, "PRINT_OUTPUT_DIR", settings.BASE_DIR / "print_output"))
        output_dir.mkdir(parents=True, exist_ok=True)

        written_files = []

        for index, doc in enumerate(rendered_documents, start=1):
            filename = output_dir / f"print_job_{print_job.id}_label_{index}.html"
            filename.write_text(doc, encoding="utf-8")
            written_files.append(str(filename))

        return {
            "mode": "mock_file",
            "files": written_files,
            "message": f"{len(written_files)} label file(s) written locally.",
        }


class RawSocketPrinterDispatcher(BasePrinterDispatcher):
    """
    Sends rendered content directly to a network printer over TCP.
    Useful for printers listening on port 9100.
    """

    def dispatch(self, printer, rendered_documents, print_job):
        if not printer.ip_address:
            raise PrinterDispatchError("Printer IP address is missing.")

        port = printer.port or 9100

        try:
            with socket.create_connection((printer.ip_address, port), timeout=10) as sock:
                for doc in rendered_documents:
                    if not isinstance(doc, str):
                        raise PrinterDispatchError("Rendered document must be a string.")
                    sock.sendall(doc.encode("utf-8"))
                    sock.sendall(b"\n\n")
        except OSError as exc:
            raise PrinterDispatchError(
                f"Failed to connect/send to printer {printer.name} at {printer.ip_address}:{port}. {exc}"
            ) from exc

        return {
            "mode": "raw_socket",
            "printer_ip": printer.ip_address,
            "printer_port": port,
            "documents_sent": len(rendered_documents),
            "message": f"{len(rendered_documents)} document(s) sent to printer.",
        }