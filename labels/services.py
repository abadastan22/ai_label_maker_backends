import re
import socket
import tempfile
from pathlib import Path
from typing import Any

from django.utils.html import escape
from django.utils.timezone import localtime

from .exceptions import (
    PrinterAdapterNotFoundError,
    PrinterDispatchError,
)
from .models import Label, PrintJob


def _string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _join_values(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(v).strip() for v in value if str(v).strip())
    return str(value).strip()


def _safe_attr(obj: Any, attr: str, default: Any = None) -> Any:
    return getattr(obj, attr, default) if obj is not None else default


def _format_dt(value) -> str:
    if not value:
        return ""
    try:
        return localtime(value).strftime("%-m/%-d/%Y, %-I:%M:%S %p")
    except Exception:
        try:
            return localtime(value).strftime("%m/%d/%Y, %I:%M:%S %p")
        except Exception:
            return str(value)


def render_label_html(
    title: str,
    prepared_at_text: str,
    use_by_text: str,
    prepared_by_text: str,
    station_text: str,
    quantity_text: str,
    batch_code_text: str,
    allergens_text: str,
    notes_text: str,
    paper_size: str = "4x2",
) -> str:
    esc = lambda value: escape(value or "")

    details = []

    if prepared_at_text:
        details.append(f'<div style="margin-bottom:4px;">Prep: {esc(prepared_at_text)}</div>')

    if use_by_text:
        details.append(
            f'<div style="margin-bottom:8px; color:#d62828;">Use By: {esc(use_by_text)}</div>'
        )

    if prepared_by_text:
        details.append(f'<div>Prepared By: {esc(prepared_by_text)}</div>')

    if station_text:
        details.append(f'<div>Station: {esc(station_text)}</div>')

    if quantity_text:
        details.append(f'<div>Qty: {esc(quantity_text)}</div>')

    if batch_code_text:
        details.append(f'<div>Batch: {esc(batch_code_text)}</div>')

    if allergens_text:
        details.append(f'<div>Allergens: {esc(allergens_text)}</div>')

    if notes_text:
        details.append(f'<div>Notes: {esc(notes_text)}</div>')

    width_map = {
        "4x2": ("4in", "2in"),
        "4×2": ("4in", "2in"),
        "3x2": ("3in", "2in"),
        "3×2": ("3in", "2in"),
        "2x1": ("2in", "1in"),
        "2×1": ("2in", "1in"),
    }
    width, min_height = width_map.get((paper_size or "4x2").strip(), ("4in", "2in"))

    return f"""
    <div data-paper-size="{escape(paper_size or '4x2')}" style="
        width: {width};
        min-height: {min_height};
        box-sizing: border-box;
        padding: 12px;
        font-family: Arial, sans-serif;
        border: 1px solid #000;
        background: #fff;
        color: #000;
    ">
        <div style="font-size: 11px; letter-spacing: 2px; color: #667085; margin-bottom: 10px;">
            FOOD PREP LABEL
        </div>

        <div style="font-size: 18px; font-weight: 700; margin-bottom: 10px;">
            {esc(title)}
        </div>

        <div style="font-size: 12px; line-height: 1.4;">
            {"".join(details)}
        </div>
    </div>
    """.strip()


def build_label_body_from_prep_task(prep_task) -> str:
    prep_item = _safe_attr(prep_task, "prep_item")

    prepared_at_text = _format_dt(_safe_attr(prep_task, "prepared_at"))
    use_by_text = _format_dt(
        _safe_attr(prep_task, "expires_at") or _safe_attr(prep_task, "use_by")
    )

    quantity = _safe_attr(prep_task, "quantity")
    unit = _string(_safe_attr(prep_task, "unit"))
    qty_text = " ".join(part for part in [_string(quantity), unit] if part).strip()

    prepared_by = _string(
        _safe_attr(prep_task, "prepared_by_name")
        or _safe_attr(prep_task, "prepared_by_text")
        or _safe_attr(_safe_attr(prep_task, "prepared_by"), "get_full_name", lambda: "")()
        or _safe_attr(_safe_attr(prep_task, "prepared_by"), "username")
    )

    station_text = _string(
        _safe_attr(prep_task, "station")
        or _safe_attr(prep_item, "station")
        or _safe_attr(_safe_attr(prep_task, "department"), "name")
    )

    batch_code_text = _string(
        _safe_attr(prep_task, "batch_code")
        or _safe_attr(prep_item, "batch_code")
    )

    allergens_text = _join_values(
        _safe_attr(prep_task, "allergens_text")
        or _safe_attr(prep_task, "allergen_info")
        or _safe_attr(prep_item, "allergens_text")
        or _safe_attr(prep_item, "allergen_info")
        or _safe_attr(prep_item, "allergens")
    )

    notes_text = _string(
        _safe_attr(prep_task, "notes")
        or _safe_attr(prep_item, "storage_notes")
        or _safe_attr(prep_item, "notes")
    )

    body_lines = [
        f"Prepared: {prepared_at_text}" if prepared_at_text else "",
        f"Expires: {use_by_text}" if use_by_text else "",
        f"Qty: {qty_text}" if qty_text else "",
        f"Prepared By: {prepared_by}" if prepared_by else "",
        f"Station: {station_text}" if station_text else "",
        f"Batch: {batch_code_text}" if batch_code_text else "",
        f"Allergens: {allergens_text}" if allergens_text else "",
        f"Notes: {notes_text}" if notes_text else "",
    ]

    return "\n".join(line for line in body_lines if line)


def build_label_from_prep_task(prep_task, paper_size: str = "4x2") -> Label:
    prep_item = _safe_attr(prep_task, "prep_item")

    title = _string(
        _safe_attr(prep_task, "item_name_override")
        or _safe_attr(prep_task, "name")
        or _safe_attr(prep_item, "name")
        or "Prep Label"
    )

    prepared_at_text = _format_dt(_safe_attr(prep_task, "prepared_at"))
    use_by_text = _format_dt(
        _safe_attr(prep_task, "expires_at") or _safe_attr(prep_task, "use_by")
    )

    prepared_by_text = _string(
        _safe_attr(prep_task, "prepared_by_name")
        or _safe_attr(prep_task, "prepared_by_text")
        or _safe_attr(_safe_attr(prep_task, "prepared_by"), "get_full_name", lambda: "")()
        or _safe_attr(_safe_attr(prep_task, "prepared_by"), "username")
    )

    station_text = _string(
        _safe_attr(prep_task, "station")
        or _safe_attr(prep_item, "station")
        or _safe_attr(_safe_attr(prep_task, "department"), "name")
    )

    quantity_value = _safe_attr(prep_task, "quantity")
    quantity_unit = _string(_safe_attr(prep_task, "unit"))
    quantity_text = " ".join(
        part for part in [_string(quantity_value), quantity_unit] if part
    ).strip()

    batch_code_text = _string(
        _safe_attr(prep_task, "batch_code")
        or _safe_attr(prep_item, "batch_code")
    )

    allergens_text = _join_values(
        _safe_attr(prep_task, "allergens_text")
        or _safe_attr(prep_task, "allergen_info")
        or _safe_attr(prep_item, "allergens_text")
        or _safe_attr(prep_item, "allergen_info")
        or _safe_attr(prep_item, "allergens")
    )

    notes_text = _string(
        _safe_attr(prep_task, "notes")
        or _safe_attr(prep_item, "storage_notes")
        or _safe_attr(prep_item, "notes")
    )

    label_body = build_label_body_from_prep_task(prep_task)
    rendered_html = render_label_html(
        title=title,
        prepared_at_text=prepared_at_text,
        use_by_text=use_by_text,
        prepared_by_text=prepared_by_text,
        station_text=station_text,
        quantity_text=quantity_text,
        batch_code_text=batch_code_text,
        allergens_text=allergens_text,
        notes_text=notes_text,
        paper_size=paper_size,
    )

    defaults = {
        "label_title": title,
        "label_body": label_body,
        "paper_size": paper_size,
        "rendered_html": rendered_html,
        "title": title,
        "item_name": title,
        "payload": label_body,
        "html_preview": rendered_html,
        "prepared_at_text": prepared_at_text,
        "use_by_text": use_by_text,
        "prepared_by_text": prepared_by_text,
        "station_text": station_text,
        "quantity_text": quantity_text,
        "batch_code_text": batch_code_text,
        "allergens_text": allergens_text,
        "notes_text": notes_text,
    }

    label, _ = Label.objects.update_or_create(
        prep_task=prep_task,
        defaults=defaults,
    )
    return label


class PrinterService:
    WINDOWS_DRIVER_TYPES = {"windows", "pywin32", "win32", "windows_spooler"}
    RAW_TCP_DRIVER_TYPES = {"raw_tcp", "tcp", "socket"}
    MOCK_DRIVER_TYPES = {"mock_file"}
    HTML_PREVIEW_DRIVER_TYPES = {"html_preview"}
    PDF_DRIVER_TYPES = {"pdf_file"}
    ZPL_DRIVER_TYPES = {"zebra_zpl"}

    def dispatch_print_job(self, print_job: PrintJob) -> dict:
        printer = print_job.printer

        if not printer:
            self._fail(print_job, "Print job has no printer assigned.")
            raise PrinterDispatchError("No printer assigned.")

        driver_type = (printer.driver_type or "windows_spooler").strip().lower()
        printer_name = (
            getattr(printer, "device_name", None)
            or getattr(printer, "name", "")
            or ""
        ).strip()
        printer_ip = (getattr(printer, "ip_address", None) or "").strip()
        printer_port = int(getattr(printer, "port", 9100) or 9100)

        items = list(print_job.items.select_related("label").all())
        if not items:
            self._fail(print_job, "Print job has no items.")
            raise PrinterDispatchError("No print items.")

        try:
            if driver_type in self.WINDOWS_DRIVER_TYPES:
                if not printer_name:
                    raise PrinterDispatchError("Printer device_name not configured.")
                result = self._print_windows_direct(printer, printer_name, items)

            elif driver_type in self.RAW_TCP_DRIVER_TYPES:
                if printer_name and self._windows_printer_exists(printer_name):
                    result = self._print_windows_direct(printer, printer_name, items)
                else:
                    if not printer_ip:
                        raise PrinterDispatchError(
                            "raw_tcp printer requires ip_address when no Windows device_name is available."
                        )
                    result = self._print_raw_tcp(printer_ip, printer_port, items)

            elif driver_type in self.MOCK_DRIVER_TYPES:
                result = self._print_mock_file(print_job, items)

            elif driver_type in self.HTML_PREVIEW_DRIVER_TYPES:
                result = self._print_html_preview(print_job, items)

            elif driver_type in self.PDF_DRIVER_TYPES:
                raise PrinterAdapterNotFoundError("pdf_file is not implemented yet.")

            elif driver_type in self.ZPL_DRIVER_TYPES:
                raise PrinterAdapterNotFoundError("zebra_zpl is not implemented yet.")

            else:
                raise PrinterAdapterNotFoundError(
                    f"No adapter for driver_type '{driver_type}'"
                )

        except PrinterDispatchError as exc:
            self._fail(print_job, str(exc))
            raise
        except Exception as exc:
            self._fail(print_job, str(exc))
            raise PrinterDispatchError(str(exc)) from exc

        self._mark_printed(print_job)
        return result

    def _windows_printer_exists(self, printer_name: str) -> bool:
        try:
            import win32print  # type: ignore
        except ImportError:
            return False

        available = [
            p[2]
            for p in win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
        ]
        return printer_name in available

    def _print_windows_direct(self, printer, printer_name: str, items) -> dict:
        try:
            import win32api  # type: ignore
            import win32con  # type: ignore
            import win32print  # type: ignore
            import win32ui  # type: ignore
        except ImportError as exc:
            raise PrinterDispatchError("pywin32 is not installed.") from exc

        available = [
            p[2]
            for p in win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
        ]
        if printer_name not in available:
            raise PrinterDispatchError(
                f"Printer '{printer_name}' not found. Available: {available}"
            )

        try:
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
        except Exception as exc:
            raise PrinterDispatchError(
                f"Unable to create printer DC for '{printer_name}': {exc}"
            ) from exc

        try:
            dpi_x = hdc.GetDeviceCaps(88)
            dpi_y = hdc.GetDeviceCaps(90)

            width_in, height_in = self._paper_dimensions(
                getattr(printer, "paper_size", None)
                or getattr(items[0].label, "paper_size", None)
                or "4x2"
            )

            page_width = int(width_in * dpi_x)
            page_height = int(height_in * dpi_y)

            margin_x = int(0.08 * dpi_x)
            margin_y = int(0.06 * dpi_y)
            inner_width = page_width - (2 * margin_x)

            is_small = width_in <= 2.1 or height_in <= 1.1
            sizes = self._font_profile(dpi_y, compact=is_small)

            fonts = {
                "header": win32ui.CreateFont({
                    "name": "Arial",
                    "height": -sizes["header"],
                    "weight": 500,
                }),
                "title": win32ui.CreateFont({
                    "name": "Arial",
                    "height": -sizes["title"],
                    "weight": 800,
                }),
                "body": win32ui.CreateFont({
                    "name": "Arial",
                    "height": -sizes["body"],
                    "weight": 400,
                }),
                "body_bold": win32ui.CreateFont({
                    "name": "Arial",
                    "height": -sizes["body"],
                    "weight": 700,
                }),
                "small": win32ui.CreateFont({
                    "name": "Arial",
                    "height": -sizes["small"],
                    "weight": 400,
                }),
            }

            red_color = win32api.RGB(220, 40, 40)
            black_color = win32api.RGB(0, 0, 0)
            gray_color = win32api.RGB(102, 102, 102)

            for item in items:
                label = item.label
                copies = max(1, int(item.copies or 1))
                parsed = self._parse_label_fields(label)

                for _ in range(copies):
                    hdc.StartDoc(f"Label {label.id}")
                    hdc.StartPage()

                    pen = win32ui.CreatePen(win32con.PS_SOLID, 1, black_color)
                    old_pen = hdc.SelectObject(pen)

                    left = margin_x
                    top = margin_y
                    right = page_width - margin_x
                    bottom = page_height - margin_y

                    hdc.MoveTo((left, top))
                    hdc.LineTo((right, top))
                    hdc.LineTo((right, bottom))
                    hdc.LineTo((left, bottom))
                    hdc.LineTo((left, top))

                    hdc.SelectObject(old_pen)

                    x = margin_x + int(0.05 * dpi_x)
                    y = margin_y + int(0.04 * dpi_y)
                    text_width = inner_width - int(0.10 * dpi_x)

                    hdc.SetTextColor(gray_color)
                    hdc.SelectObject(fonts["header"])
                    hdc.TextOut(x, y, "FOOD PREP LABEL")
                    y += sizes["header"] + int(0.02 * dpi_y)

                    hdc.SetTextColor(black_color)
                    hdc.SelectObject(fonts["title"])
                    y = self._draw_wrapped_text(
                        hdc=hdc,
                        text=parsed["title"],
                        x=x,
                        y=y,
                        max_width=text_width,
                        line_height=int(sizes["title"] * 0.95),
                    )

                    y += int(0.01 * dpi_y)

                    hdc.SelectObject(fonts["body"])
                    prep_line = f"Prep: {parsed['prepared']}" if parsed["prepared"] else ""
                    if prep_line:
                        hdc.SetTextColor(black_color)
                        y = self._draw_wrapped_text(
                            hdc=hdc,
                            text=prep_line,
                            x=x,
                            y=y,
                            max_width=text_width,
                            line_height=int(sizes["body"] * 0.95),
                        )

                    use_by_line = f"Use By: {parsed['use_by']}" if parsed["use_by"] else ""
                    if use_by_line:
                        hdc.SetTextColor(red_color)
                        y = self._draw_wrapped_text(
                            hdc=hdc,
                            text=use_by_line,
                            x=x,
                            y=y,
                            max_width=text_width,
                            line_height=int(sizes["body"] * 0.95),
                        )

                    y += int(0.01 * dpi_y)
                    hdc.SetTextColor(black_color)

                    detail_lines = [
                        ("Prepared By", parsed["prepared_by"]),
                        ("Station", parsed["station"]),
                        ("Qty", parsed["qty"]),
                        ("Batch", parsed["batch"]),
                        ("Allergens", parsed["allergens"]),
                    ]

                    for label_name, value in detail_lines:
                        if not value:
                            continue

                        prefix = f"{label_name}: "

                        hdc.SelectObject(fonts["body_bold"])
                        hdc.TextOut(x, y, prefix)
                        prefix_width = hdc.GetTextExtent(prefix)[0]

                        hdc.SelectObject(fonts["body"])
                        y = self._draw_wrapped_text(
                            hdc=hdc,
                            text=value,
                            x=x + prefix_width,
                            y=y,
                            max_width=text_width - prefix_width,
                            line_height=int(sizes["body"] * 0.95),
                            first_line_prefix_x=x,
                        )

                        if y > page_height - margin_y - int(0.12 * dpi_y):
                            break

                    hdc.EndPage()
                    hdc.EndDoc()

        except Exception as exc:
            try:
                hdc.AbortDoc()
            except Exception:
                pass
            raise PrinterDispatchError(
                f"Direct Windows printing failed for '{printer_name}': {exc}"
            ) from exc
        finally:
            try:
                hdc.DeleteDC()
            except Exception:
                pass

        return {
            "status": "sent",
            "transport": "windows_direct_polished",
            "printer": printer_name,
            "items": len(items),
        }

    def _parse_label_fields(self, label) -> dict:
        title = _string(label.title or label.item_name or label.label_title)

        result = {
            "title": title,
            "prepared": _string(label.prepared_at_text),
            "use_by": _string(label.use_by_text),
            "prepared_by": _string(label.prepared_by_text),
            "station": _string(label.station_text),
            "qty": _string(label.quantity_text),
            "batch": _string(label.batch_code_text),
            "allergens": _string(label.allergens_text),
        }

        if all(result.values()):
            return result

        body = _string(label.payload or label.label_body)

        line_map = {
            "prepared": [r"^Prepared:\s*(.+)$", r"^Prep:\s*(.+)$"],
            "use_by": [r"^Expires:\s*(.+)$", r"^Use By:\s*(.+)$"],
            "prepared_by": [r"^Prepared By:\s*(.+)$"],
            "station": [r"^Station:\s*(.+)$", r"^Storage:\s*(.+)$"],
            "qty": [r"^Qty:\s*(.+)$", r"^Quantity:\s*(.+)$"],
            "batch": [r"^Batch:\s*(.+)$", r"^Batch Code:\s*(.+)$"],
            "allergens": [r"^Allergens:\s*(.+)$"],
        }

        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            for key, patterns in line_map.items():
                if result[key]:
                    continue

                for pattern in patterns:
                    match = re.match(pattern, line, flags=re.IGNORECASE)
                    if match:
                        result[key] = match.group(1).strip()
                        break

        return result

    def _paper_dimensions(self, paper_size: str) -> tuple[float, float]:
        normalized = (paper_size or "").lower().replace('"', "").replace(" ", "")

        mapping = {
            "4x2": (4.0, 2.0),
            "4×2": (4.0, 2.0),
            "2x1": (2.0, 1.0),
            "2×1": (2.0, 1.0),
            "3x2": (3.0, 2.0),
            "3×2": (3.0, 2.0),
        }

        return mapping.get(normalized, (4.0, 2.0))

    def _font_profile(self, dpi_y: int, compact: bool = False) -> dict:
        if compact:
            return {
                "header": max(10, int(0.07 * dpi_y)),
                "title": max(18, int(0.16 * dpi_y)),
                "body": max(11, int(0.10 * dpi_y)),
                "small": max(9, int(0.08 * dpi_y)),
            }

        return {
            "header": max(12, int(0.08 * dpi_y)),
            "title": max(26, int(0.20 * dpi_y)),
            "body": max(13, int(0.11 * dpi_y)),
            "small": max(10, int(0.09 * dpi_y)),
        }

    def _draw_wrapped_text(
        self,
        hdc,
        text: str,
        x: int,
        y: int,
        max_width: int,
        line_height: int,
        first_line_prefix_x: int | None = None,
    ) -> int:
        words = text.split()
        if not words:
            return y + line_height

        current = words[0]
        start_x = x
        base_max_width = max_width

        for word in words[1:]:
            trial = f"{current} {word}"
            width = hdc.GetTextExtent(trial)[0]
            if width <= max_width:
                current = trial
            else:
                hdc.TextOut(start_x, y, current)
                y += line_height
                current = word
                if first_line_prefix_x is not None:
                    start_x = first_line_prefix_x
                    max_width = base_max_width + (x - first_line_prefix_x)
                else:
                    start_x = x
                    max_width = base_max_width

        hdc.TextOut(start_x, y, current)
        return y + line_height

    def _print_raw_tcp(self, ip_address: str, port: int, items) -> dict:
        sent_items = 0

        for item in items:
            label = item.label
            copies = max(1, int(item.copies or 1))

            payload_text = self._build_raw_payload(label)
            payload_bytes = payload_text.encode("utf-8")

            for _ in range(copies):
                try:
                    with socket.create_connection((ip_address, port), timeout=10) as sock:
                        sock.sendall(payload_bytes)
                except OSError as exc:
                    raise PrinterDispatchError(
                        f"raw_tcp dispatch to {ip_address}:{port} failed: {exc}"
                    ) from exc

            sent_items += 1

        return {
            "status": "sent",
            "transport": "raw_tcp",
            "ip_address": ip_address,
            "port": port,
            "items": sent_items,
        }

    def _build_raw_payload(self, label) -> str:
        title = _string(label.title or label.item_name or label.label_title)
        body = _string(label.payload or label.label_body)
        return f"{title}\n{body}\n\n"

    def _print_mock_file(self, print_job: PrintJob, items) -> dict:
        output_dir = Path(tempfile.gettempdir()) / "ai_label_maker" / "mock_prints"
        output_dir.mkdir(parents=True, exist_ok=True)

        written_files = []

        for item in items:
            label = item.label
            copies = max(1, int(item.copies or 1))

            for copy_num in range(1, copies + 1):
                file_path = output_dir / (
                    f"print_job_{print_job.id}_item_{item.id}_copy_{copy_num}.html"
                )
                file_path.write_text(self._wrap_html(label), encoding="utf-8")
                written_files.append(str(file_path))

        return {
            "status": "sent",
            "transport": "mock_file",
            "files": written_files,
            "items": len(items),
        }

    def _print_html_preview(self, print_job: PrintJob, items) -> dict:
        output_dir = Path(tempfile.gettempdir()) / "ai_label_maker" / "html_preview"
        output_dir.mkdir(parents=True, exist_ok=True)

        written_files = []

        for item in items:
            label = item.label
            file_path = output_dir / f"print_job_{print_job.id}_item_{item.id}.html"
            file_path.write_text(self._wrap_html(label), encoding="utf-8")
            written_files.append(str(file_path))

        return {
            "status": "sent",
            "transport": "html_preview",
            "files": written_files,
            "items": len(items),
        }

    def _wrap_html(self, label) -> str:
        html = label.html_preview or label.rendered_html or ""
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
@page {{ margin: 0.1in; }}
body {{ margin: 0; padding: 0.1in; }}
</style>
</head>
<body>
{html}
</body>
</html>
"""

    def _mark_printed(self, job: PrintJob) -> None:
        job.status = PrintJob.STATUS_PRINTED
        job.error_message = ""
        job.save(update_fields=["status", "error_message", "updated_at"])

    def _fail(self, job: PrintJob, message: str) -> None:
        job.status = PrintJob.STATUS_FAILED
        job.error_message = (message or "")[:2000]
        job.save(update_fields=["status", "error_message", "updated_at"])