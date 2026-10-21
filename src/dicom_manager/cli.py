# DICOM-Manager - Arguments parser.
# Author: Pascal Malouin (https://github.com/EGOUID0)
# Project: https://github.com/EGOUID0/DICOM-Manager
# Created: 2026-10-09

import argparse
from pathlib import Path
import sys
import pydicom
from rich.console import Console

from . import __version__
from .core.config import load_values, write_template
from .core.discovery import locate_dicom_files, locate_dicomdirs
from .core.fileset import create_dicomdir, inspect_fileset
from .core.operations import transform
from .core.organize import organize
from .core.output import default_output
from .defaults import ANONYMIZE_DEFAULTS, INSPECT_DEFAULTS
from .output.render import print_fileset_report, print_inspection, print_paths

console = Console(stderr=True)


def directory(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"not a directory: {value}")
    return path


def add_directory(parser):
    parser.add_argument("-d", "--directory", type=directory, default=Path.cwd(), help="Source directory")
    parser.add_argument("--plain", action="store_true", help="Plain text output for CLI processing")


def add_layout_options(parser):
    parser.add_argument("-o", "--output", type=Path, help="Output directory")
    layout = parser.add_mutually_exclusive_group()
    layout.add_argument("--flat", action="store_true", help="Put all instances in one directory; generated names are used")
    layout.add_argument("--hierarchical", action="store_true", help="Generate PT/ST/SE/IM DICOM File-set style hierarchy")
    parser.add_argument("--rename", action="store_true", help="Generate IMxxxxxx filenames without changing the selected layout")
    parser.add_argument("--dcm-extension", action="store_true", help="Ensure output instance filenames have a .dcm extension")
    parser.add_argument("--dicomdir", action="store_true", help="Create DICOMDIR after writing output")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output directory")


def add_write_options(parser):
    add_directory(parser)
    parser.add_argument("--from-file", type=Path, help="Values from JSON, TOML or INI")
    add_layout_options(parser)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dicom-manager", description="Cross-platform DICOM management tools")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    locate = sub.add_parser("locate", help="Locate DICOM files or DICOMDIR")
    add_directory(locate)
    locate.add_argument("kind", choices=("dcm", "dicomdir", "all"), nargs="?", default="all")

    read = sub.add_parser("read", help="Read complete DICOM datasets")
    add_directory(read)

    inspect = sub.add_parser("inspect", help="Inspect selected DICOM attributes or File-set compatibility")
    add_directory(inspect)
    inspect.add_argument("--fields", nargs="+", default=list(INSPECT_DEFAULTS))
    inspect.add_argument("--fileset", action="store_true", help="Inspect DICOM File-set/DICOMDIR compatibility")
    inspect_layout = inspect.add_mutually_exclusive_group()
    inspect_layout.add_argument("--multi-file", dest="inspect_layout", action="store_const", const="multi", help="Show one comparison table for all files")
    inspect_layout.add_argument("--per-file", dest="inspect_layout", action="store_const", const="per-file", help="Show one table per DICOM file")
    inspect.set_defaults(inspect_layout="auto")

    anonymize = sub.add_parser("anonymize", help="Modify only the supported anonymization fields")
    add_write_options(anonymize)
    anonymize.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="Override a permitted anonymization field")

    modify = sub.add_parser("modify", help="Modify arbitrary existing DICOM fields")
    add_write_options(modify)
    modify.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")

    org = sub.add_parser("organize", help="Copy/reorganize DICOM files without modifying DICOM data")
    add_directory(org)
    add_layout_options(org)
    org.add_argument("--in-place", action="store_true", help="Add DICOMDIR directly to source; cannot rename or reorganize files")

    template = sub.add_parser("template", help="Create a values template in the current directory")
    template.add_argument("kind", choices=("anonymize", "modify"))
    template.add_argument("--format", choices=("toml", "json", "ini"), default="toml")
    template.add_argument("--output", type=Path)
    return p


def layout(args) -> str:
    return "flat" if args.flat else "hierarchical" if args.hierarchical else "preserve"


def validate_fileset_options(args):
    if args.dicomdir and args.dcm_extension:
        raise ValueError("--dcm-extension cannot be used with --dicomdir: a DICOM File ID cannot contain a dot/extension")


def run_write(args, command: str) -> int:
    validate_fileset_options(args)
    source = args.directory.resolve()
    output = args.output.expanduser().resolve() if args.output else default_output(source, command)
    if output == source or source in output.parents:
        raise ValueError("Output must not be the source directory or inside it")

    if command == "anonymize":
        values = dict(ANONYMIZE_DEFAULTS)
        if args.from_file:
            requested = load_values(args.from_file)
            invalid = sorted(set(requested) - set(ANONYMIZE_DEFAULTS))
            if invalid:
                raise ValueError("Unsupported anonymization fields: " + ", ".join(invalid))
            values.update(requested)
    else:
        values = load_values(args.from_file) if args.from_file else {}
    for item in args.set:
        if "=" not in item:
            raise ValueError(f"Invalid --set value: {item}; expected KEY=VALUE")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("--set requires a nonempty field keyword")
        if command == "anonymize" and key not in ANONYMIZE_DEFAULTS:
            raise ValueError(f"Unsupported anonymization field: {key}")
        values[key] = value
    if not values:
        raise ValueError("modify requires --from-file or at least one --set KEY=VALUE")

    rename = args.rename or args.hierarchical or args.flat
    count, totals = transform(source, output, values, layout(args), args.overwrite,
                              rename=rename, dcm_extension=args.dcm_extension)
    if args.dicomdir:
        create_dicomdir(output)
    if args.plain:
        print(f"output={output}")
        print(f"files={count}")
    else:
        console.print(f"[green]Wrote {count} DICOM file(s) to[/] {output}")
        for key, changed in totals.items():
            console.print(f"  {key}: {changed} value(s) changed")
    return 0


def run_organize(args) -> int:
    validate_fileset_options(args)
    source = args.directory.resolve()
    if args.in_place:
        if args.output or args.flat or args.hierarchical or args.rename or args.dcm_extension:
            raise ValueError("--in-place may only be used to add --dicomdir; it cannot rename, move, or copy instances")
        if not args.dicomdir:
            raise ValueError("--in-place currently requires --dicomdir")
        target = create_dicomdir(source)
        if args.plain:
            print(f"dicomdir={target}")
        else:
            console.print(f"[green]Created[/] {target}")
        return 0

    output = args.output.expanduser().resolve() if args.output else default_output(source, "organize")
    if output == source or source in output.parents:
        raise ValueError("Output must not be the source directory or inside it")
    count = organize(source, output, layout(args), args.overwrite,
                     rename=args.rename, dcm_extension=args.dcm_extension)
    if args.dicomdir:
        create_dicomdir(output)
    if args.plain:
        print(f"output={output}")
        print(f"files={count}")
    else:
        console.print(f"[green]Organized {count} DICOM file(s) into[/] {output}")
        console.print("[dim]DICOM instance bytes were copied unchanged.[/]")
    return 0


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "locate":
            paths = []
            if args.kind in {"dcm", "all"}:
                paths += locate_dicom_files(args.directory)
            if args.kind in {"dicomdir", "all"}:
                paths += locate_dicomdirs(args.directory)
            print_paths(sorted(paths), args.plain)
            return 0

        if args.command == "read":
            for path in locate_dicom_files(args.directory):
                ds = pydicom.dcmread(path)
                if not args.plain:
                    console.print(f"[bold]{path}[/]")
                print(ds)
            return 0

        if args.command == "inspect":
            if args.fileset:
                print_fileset_report(inspect_fileset(args.directory), args.plain)
                return 0
            records = []
            for path in locate_dicom_files(args.directory):
                ds = pydicom.dcmread(path, stop_before_pixels=True)
                values = [(key, str(getattr(ds, key, ""))) for key in args.fields]
                records.append((path, values))
            print_inspection(records, args.directory, args.plain, args.inspect_layout)
            return 0

        if args.command in {"anonymize", "modify"}:
            return run_write(args, args.command)

        if args.command == "organize":
            return run_organize(args)

        if args.command == "template":
            path = args.output or Path.cwd() / f"{args.kind}.{args.format}"
            values = dict(ANONYMIZE_DEFAULTS) if args.kind == "anonymize" else {
                "PatientName": "EXAMPLE^PATIENT", "StudyDescription": "Example value"
            }
            write_template(path, values)
            console.print(f"[green]Created[/] {path}")
            return 0
    except (OSError, ValueError, NotImplementedError) as exc:
        console.print(f"[red]Error:[/] {exc}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
