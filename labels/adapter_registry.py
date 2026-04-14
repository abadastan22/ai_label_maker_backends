from labels.adapters.html_preview import HtmlPreviewPrinterAdapter
from labels.adapters.mock_file import MockFilePrinterAdapter
from labels.adapters.pdf_file import PdfFilePrinterAdapter
from labels.adapters.raw_tcp import RawTcpPrinterAdapter
from labels.adapters.windows_spooler import WindowsSpoolerPrinterAdapter
from labels.adapters.zpl import ZplPrinterAdapter
from labels.exceptions import PrinterAdapterNotFoundError


class PrinterAdapterRegistry:
    def __init__(self):
        self._adapters = {
            MockFilePrinterAdapter.driver_type: MockFilePrinterAdapter(),
            RawTcpPrinterAdapter.driver_type: RawTcpPrinterAdapter(),
            ZplPrinterAdapter.driver_type: ZplPrinterAdapter(),
            HtmlPreviewPrinterAdapter.driver_type: HtmlPreviewPrinterAdapter(),
            PdfFilePrinterAdapter.driver_type: PdfFilePrinterAdapter(),
            WindowsSpoolerPrinterAdapter.driver_type: WindowsSpoolerPrinterAdapter(),
        }

    def get_adapter(self, driver_type: str):
        adapter = self._adapters.get(driver_type)
        if not adapter:
            raise PrinterAdapterNotFoundError(
                f"No printer adapter registered for driver_type='{driver_type}'."
            )
        return adapter