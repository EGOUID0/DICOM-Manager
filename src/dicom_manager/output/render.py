# DICOM-Manager - Rich output.
# Author: Pascal Malouin (https://github.com/EGOUID0)
# Project: https://github.com/EGOUID0/DICOM-Manager
# Created: 2026-10-09

from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

def print_paths(paths: list[Path], plain: bool) -> None:
    if plain:
        for path in paths:
            print(path)
        return
    table = Table("#", "Path", title=f"{len(paths)} result(s)")
    for i, path in enumerate(paths, 1):
        table.add_row(str(i), str(path))
    console.print(table)


def print_inspection_plain(records):
    for path, values in records:
        print(f"file={path}")
        for key, value in values:
            print(f"{key}={value}")


def _relative_display(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _multi_file_fits(records, root: Path, console_width: int) -> bool:
    if not records:
        return True
    headers = [key for key, _ in records[0][1]]
    file_width = max(len("File"), max(len(_relative_display(path, root)) for path, _ in records))
    widths = [file_width]
    for index, header in enumerate(headers):
        value_width = max(len(str(values[index][1])) for _, values in records)
        widths.append(max(len(header), value_width))
    overhead = 3 * len(widths) + 1
    return sum(widths) + overhead <= console_width


def print_inspection_multi(records, root: Path) -> None:
    if not records:
        console.print("[yellow]No DICOM files found.[/]")
        return
    headers = [key for key, _ in records[0][1]]
    table = Table(show_lines=False)
    table.add_column("File", overflow="fold", no_wrap=False)
    for header in headers:
        table.add_column(header, overflow="fold", no_wrap=False)
    for path, values in records:
        table.add_row(_relative_display(path, root), *(value for _, value in values))
    console.print(table)


def print_inspection_per_file(records, root: Path) -> None:
    for index, (path, values) in enumerate(records):
        if index:
            console.print()
        table = Table("Attribute", "Value", title=_relative_display(path, root), title_justify="left")
        table.columns[0].no_wrap = True
        table.columns[1].overflow = "fold"
        table.columns[1].no_wrap = False
        for key, value in values:
            table.add_row(key, value)
        console.print(table)


def print_inspection(records, root: Path, plain: bool, layout: str = "auto") -> str:
    if plain:
        print_inspection_plain(records)
        return "plain"
    selected = layout
    if selected == "auto":
        selected = "multi" if _multi_file_fits(records, root, console.width) else "per-file"
    if selected == "multi":
        print_inspection_multi(records, root)
    else:
        print_inspection_per_file(records, root)
    return selected


def print_fileset_report(report, plain=False):
    if plain:
        print(f"files={report.files}")
        print(f'dicomdir={"yes" if report.dicomdir_present else "no"}')
        print(f'file_id_compliant={"yes" if report.compliant else "no"}')
        print(f"invalid_directories={len(report.invalid_directories)}")
        print(f"invalid_files={len(report.invalid_files)}")
        for path in report.invalid_files:
            print(f"invalid_file={path}")
        return
    table = Table("Property", "Value", title="DICOM File-set compatibility")
    table.add_row("DICOM files", str(report.files))
    table.add_row("DICOMDIR present", "Yes" if report.dicomdir_present else "No")
    table.add_row("File ID compliant", "Yes" if report.compliant else "No")
    table.add_row("Non-compliant directories", str(len(report.invalid_directories)))
    table.add_row("Non-compliant files", str(len(report.invalid_files)))
    console.print(table)
    if report.invalid_files:
        console.print("[yellow]Examples:[/]")
        for path in report.invalid_files[:10]:
            console.print(f"  {path}")
        if len(report.invalid_files) > 10:
            console.print(f"  ... and {len(report.invalid_files) - 10} more")
        console.print("[dim]Recommendation: use --rename and/or --hierarchical before --dicomdir.[/]")
