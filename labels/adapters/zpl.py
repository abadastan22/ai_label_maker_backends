import socket

from labels.exceptions import PrinterDispatchError
from .base import BasePrinterAdapter


class ZplPrinterAdapter(BasePrinterAdapter):
    driver_type = "zpl"

    def dispatch(self, printer, documents, print_job):
        if not printer.ip_address:
            raise PrinterDispatchError("ZPL printer IP address is missing.")

        port = printer.port or 9100
        timeout = printer.connection_options.get("timeout", 10)

        try:
            with socket.create_connection((printer.ip_address, port), timeout=timeout) as sock:
                for document in documents:
                    if not isinstance(document, str):
                        raise PrinterDispatchError("ZPL adapter expects string payloads.")
                    sock.sendall(document.encode("utf-8"))
        except OSError as exc:
            raise PrinterDispatchError(
                f"ZPL dispatch failed to {printer.ip_address}:{port}: {exc}"
            ) from exc

        return {
            "mode": self.driver_type,
            "printer_ip": printer.ip_address,
            "printer_port": port,
            "documents_sent": len(documents),
            "message": f"{len(documents)} ZPL label(s) sent.",
        }