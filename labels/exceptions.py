class PrinterDispatchError(Exception):
    """Raised when a print job cannot be dispatched."""


class PrinterAdapterNotFoundError(PrinterDispatchError):
    """Raised when no adapter exists for the requested driver_type."""


class PrinterPayloadError(PrinterDispatchError):
    """Raised when the payload for a printer cannot be built."""