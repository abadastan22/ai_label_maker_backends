from abc import ABC, abstractmethod


class BasePrinterAdapter(ABC):
    driver_type = "Window"

    @abstractmethod
    def dispatch(self, printer, documents, print_job):
        """
        documents: list[str | bytes]
        Returns dict with dispatch metadata.
        """
        raise NotImplementedError