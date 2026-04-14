import socket

from labels.exceptions import PrinterDispatchError
from .base import BasePrinterAdapter


class RawTcpPrinterAdapter(BasePrinterAdapter):
    driver_type = "raw_tcp"

    def dispatch(self, printer, documents, print_job):
        if not printer.ip_address:
            raise PrinterDispatchError("Printer IP address is missing.")

        port = printer.port or 9100
        timeout = printer.connection_options.get("timeout", 10)

        try:
            with socket.create_connection((printer.ip_address, port), timeout=timeout) as sock:
                for document in documents:
                    payload = document.encode("utf-8") if isinstance(document, str) else document
                    sock.sendall(payload)
                    sock.sendall(b"\n")
        except OSError as exc:
            raise PrinterDispatchError(
                f"Raw TCP dispatch failed to {printer.ip_address}:{port}: {exc}"
            ) from exc

        return {
            "mode": self.driver_type,
            "printer_ip": printer.ip_address,
            "printer_port": port,
            "documents_sent": len(documents),
            "message": f"{len(documents)} raw TCP document(s) sent.",
        }