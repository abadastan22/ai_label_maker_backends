from labels.exceptions import PrinterDispatchError
from .base import BasePrinterAdapter

try:
    import win32api
    import win32print
except ImportError:  # pragma: no cover
    win32api = None
    win32print = None


class WindowsSpoolerPrinterAdapter(BasePrinterAdapter):
    driver_type = "windows_spooler"

    def dispatch(self, printer, documents, print_job):
        if win32print is None or win32api is None:
            raise PrinterDispatchError(
                "pywin32 is not installed. Install it on the Windows print host."
            )

        if not printer.device_name:
            raise PrinterDispatchError("Windows spooler printer requires device_name.")

        temp_files = []

        try:
            for idx, document in enumerate(documents, start=1):
                filename = f"print_job_{print_job.id}_{idx}.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(document if isinstance(document, str) else document.decode("utf-8", errors="ignore"))
                temp_files.append(filename)
                win32api.ShellExecute(
                    0,
                    "printto",
                    filename,
                    f'"{printer.device_name}"',
                    ".",
                    0,
                )
        except Exception as exc:
            raise PrinterDispatchError(
                f"Windows spooler dispatch failed for {printer.device_name}: {exc}"
            ) from exc

        return {
            "mode": self.driver_type,
            "device_name": printer.device_name,
            "documents_sent": len(documents),
            "message": f"{len(documents)} document(s) sent to Windows spooler.",
        }