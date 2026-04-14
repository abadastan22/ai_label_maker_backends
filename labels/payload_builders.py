from labels.exceptions import PrinterPayloadError


class LabelPayloadBuilder:
    @staticmethod
    def build_documents_for_driver(print_job, driver_type: str):
        items = print_job.items.select_related("label").all()
        if not items.exists():
            raise PrinterPayloadError("Print job has no items.")

        documents = []

        for item in items:
            label = item.label
            copies = item.copies or 1

            payload = LabelPayloadBuilder.build_single_payload(label, driver_type)

            for _ in range(copies):
                documents.append(payload)

        return documents

    @staticmethod
    def build_single_payload(label, driver_type: str):
        if not label:
            raise PrinterPayloadError("Print job item is missing its label.")

        if driver_type in {"mock_file", "html_preview", "pdf_file", "raw_tcp", "windows_spooler"}:
            if not label.rendered_html:
                raise PrinterPayloadError(
                    f"Label {label.id} has no rendered_html for driver {driver_type}."
                )
            return label.rendered_html

        if driver_type == "zpl":
            return LabelPayloadBuilder.build_zpl(label)

        raise PrinterPayloadError(f"Unsupported payload builder for driver '{driver_type}'.")

    @staticmethod
    def build_zpl(label):
        title = (label.label_title or "")[:40]
        body = (label.label_body or "").replace("\n", " ")[:200]

        return f"""^XA
^PW812
^LL406
^FO30,30^A0N,40,40^FD{title}^FS
^FO30,90^A0N,28,28^FD{body}^FS
^XZ"""