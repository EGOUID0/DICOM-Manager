# DICOM-Manager - Qt desktop frontend.
# Author: Pascal Malouin (https://github.com/EGOUID0)
# Project: https://github.com/EGOUID0/DICOM-Manager
# Created: 2026-10-09

import sys
import platform
import pydicom
from importlib.metadata import version as package_version, PackageNotFoundError
from PySide6 import __version__ as pyside_version
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl, qVersion
from . import __version__ as APP_VERSION
from pathlib import Path
from PySide6.QtCore import QProcess, Qt, QSettings
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QFormLayout, QTabWidget, QLineEdit, QPushButton, QFileDialog,
    QComboBox, QCheckBox, QPlainTextEdit, QLabel, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QDialog, QDialogButtonBox, QScrollArea, QFrame, QSplitter, QAbstractItemView)
from .defaults import INSPECT_DEFAULTS, ANONYMIZE_DEFAULTS
from .core.config import load_values, write_template
from .core.discovery import locate_dicom_files
import pydicom
from pydicom.datadict import keyword_dict


COMMON = tuple(dict.fromkeys((*INSPECT_DEFAULTS, "SeriesNumber", "InstanceNumber", "SeriesDescription", "SOPClassUID", "Rows", "Columns", "PixelSpacing", "ImageType")))
ALL_FIELDS = sorted(k for k in keyword_dict if k)


class FieldsDialog(QDialog):
    """Searchable field picker, with a distinct frequently-used section."""
    def __init__(self, parent, selected, modify=False, allowed=None, existing=None):
        super().__init__(parent)
        self.modify = modify
        self.existing = existing or {}
        self.setWindowTitle("Modify fields" if modify else "Inspect fields")
        self.resize(650, 650)
        self.controls = {}
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter DICOM keywords…")
        layout.addWidget(self.search)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget(); self.field_layout = QVBoxLayout(content)
        self.field_layout.addWidget(QLabel("COMMON FIELDS"))
        for keyword in COMMON:
            if allowed is None or keyword in allowed: self.add_field(keyword, selected)
        separator = QFrame(); separator.setFrameShape(QFrame.Shape.HLine)
        self.field_layout.addWidget(separator)
        self.field_layout.addWidget(QLabel("ALL OTHER DICOM FIELDS"))
        for keyword in ALL_FIELDS:
            if keyword not in COMMON and (allowed is None or keyword in allowed): self.add_field(keyword, selected)
        self.field_layout.addStretch()
        scroll.setWidget(content); layout.addWidget(scroll)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.search.textChanged.connect(self.filter_fields)

    def add_field(self, keyword, selected):
        row = QWidget(); horizontal = QHBoxLayout(row)
        horizontal.setContentsMargins(0, 1, 0, 1)
        checkbox = QCheckBox(keyword)
        checkbox.setChecked(keyword in selected)
        horizontal.addWidget(checkbox)
        value = None
        if self.modify:
            value = QLineEdit(selected.get(keyword, "") if keyword in selected else self.existing.get(keyword, ""))
            value.setPlaceholderText("New value (existing shown where unambiguous)")
            horizontal.addWidget(value, 1)
        else:
            horizontal.addStretch()
        self.field_layout.addWidget(row)
        self.controls[keyword] = (row, checkbox, value)

    def filter_fields(self, text):
        query = text.casefold().strip()
        for keyword, (row, _, _) in self.controls.items():
            row.setVisible(not query or query in keyword.casefold())

    def selection(self):
        if self.modify:
            return {k: value.text() for k, (_, checked, value) in self.controls.items() if checked.isChecked()}
        return [k for k, (_, checked, _) in self.controls.items() if checked.isChecked()]


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DICOM-Manager 2.0")
        self.resize(1150, 820)
        self.settings = QSettings("EGOUID0", "DICOM-Manager")
        self.inspect_selected = self.settings.value("inspect/fields", list(INSPECT_DEFAULTS), type=list)
        self.inspection_mode = "auto"
        self.modify_selected = {}
        self.anonymize_selected = {}
        self.proc = None
        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        title = QLabel("DICOM-Manager")
        title.setStyleSheet("font-size: 26px; font-weight: 700; margin: 6px 0 10px 0;")
        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch()
        about_button = QPushButton("?  About")
        about_button.setToolTip("About DICOM-Manager")
        about_button.clicked.connect(self.show_about)
        header.addWidget(about_button)
        outer.addLayout(header)
        self.dark = QCheckBox("Dark mode")
        self.dark.setChecked(self.settings.value("appearance/dark_mode", True, type=bool))
        self.dark.toggled.connect(self.apply_theme)
        outer.addWidget(self.dark)
        paths = QGroupBox("Source and destination")
        form = QFormLayout(paths)
        self.source = QLineEdit(self.settings.value("paths/source", str(Path.home())))
        self.output = QLineEdit(self.settings.value("paths/output", ""))
        for label, field, choose in (("Source directory", self.source, self.choose_source),
                                     ("Output directory (optional)", self.output, self.choose_output)):
            row = QHBoxLayout(); row.addWidget(field)
            btn = QPushButton("Browse…"); btn.clicked.connect(choose); row.addWidget(btn)
            form.addRow(label, row)
        outer.addWidget(paths)
        self.tabs = QTabWidget(); outer.addWidget(self.tabs)
        self.inspect_tab = QWidget(); self.tabs.addTab(self.inspect_tab, "Inspect")
        inspect_layout = QVBoxLayout(self.inspect_tab)
        field_row = QHBoxLayout()
        self.inspect_fields_button = QPushButton("Fields…")
        self.inspect_fields_button.clicked.connect(self.choose_inspect_fields)
        self.inspect_field_count = QLabel()
        field_row.addWidget(self.inspect_fields_button)
        field_row.addWidget(self.inspect_field_count)
        field_row.addStretch()
        field_row.addWidget(QLabel("Presentation"))
        self.presentation = QComboBox()
        self.presentation.addItems(["Auto", "Multi-file", "Per-file"])
        self.presentation.setCurrentText(self.settings.value("inspect/mode", "Auto"))
        self.presentation.currentTextChanged.connect(lambda v: self.settings.setValue("inspect/mode", v))
        field_row.addWidget(self.presentation)
        inspect_layout.addLayout(field_row)
        self.refresh_field_counts()
        row = QHBoxLayout()
        self.inspect_button = QPushButton("Inspect files"); self.inspect_button.clicked.connect(self.inspect_files)
        self.fileset_button = QPushButton("Inspect File-set"); self.fileset_button.clicked.connect(self.inspect_fileset)
        row.addWidget(self.inspect_button); row.addWidget(self.fileset_button)
        inspect_layout.addLayout(row)
        self.table = QTableWidget(); self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setWordWrap(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setAlternatingRowColors(True)
        inspect_layout.addWidget(self.table)
        self.ops_tab = QWidget(); self.tabs.addTab(self.ops_tab, "Process")
        ops = QFormLayout(self.ops_tab)
        self.action = QComboBox(); self.action.addItems(["organize", "anonymize", "modify"])
        ops.addRow("Action", self.action)
        self.config = QLineEdit(); cfgrow = QHBoxLayout(); cfgrow.addWidget(self.config)
        b = QPushButton("Browse…"); b.clicked.connect(self.choose_config); cfgrow.addWidget(b)
        ops.addRow("Values file (TOML / JSON / INI)", cfgrow)
        self.modify_fields_button = QPushButton("Select fields and values…")
        self.modify_fields_button.clicked.connect(self.choose_modify_fields)
        self.modify_field_count = QLabel("0 fields selected")
        modrow = QHBoxLayout(); modrow.addWidget(self.modify_fields_button); modrow.addWidget(self.modify_field_count)
        ops.addRow("Field overrides", modrow)
        self.edit_config_button = QPushButton("Edit loaded values…")
        self.edit_config_button.clicked.connect(self.edit_config)
        ops.addRow("Values file editor", self.edit_config_button)
        self.layout = QComboBox(); self.layout.addItems(["preserve", "flat", "hierarchical"])
        ops.addRow("Directory layout", self.layout)
        self.rename = QCheckBox("Rename instances to IMxxxxxx")
        self.extension = QCheckBox("Add .dcm extension")
        self.dicomdir = QCheckBox("Create DICOMDIR")
        self.in_place = QCheckBox("Add DICOMDIR in place (organize only)")
        self.overwrite = QCheckBox("Overwrite existing output directory")
        for item in (self.rename,self.extension,self.dicomdir,self.in_place,self.overwrite): ops.addRow(item)
        self.action.currentTextChanged.connect(self.update_options)
        self.in_place.toggled.connect(self.update_options)
        self.run_button = QPushButton("Run operation"); self.run_button.clicked.connect(self.run_operation)
        ops.addRow(self.run_button)
        self.template_tab = QWidget(); self.tabs.addTab(self.template_tab, "Templates")
        templates = QFormLayout(self.template_tab)
        self.template_kind = QComboBox(); self.template_kind.addItems(["anonymize", "modify"])
        templates.addRow("Template type", self.template_kind)
        self.template_format = QComboBox(); self.template_format.addItems(["toml", "json", "ini"])
        templates.addRow("Format", self.template_format)
        self.template_path = QLineEdit()
        trow = QHBoxLayout(); trow.addWidget(self.template_path)
        tbrowse = QPushButton("Save as…"); tbrowse.clicked.connect(self.choose_template_path)
        trow.addWidget(tbrowse)
        templates.addRow("Destination file", trow)
        tbutton = QPushButton("Generate template"); tbutton.clicked.connect(self.generate_template)
        templates.addRow(tbutton)
        outer.addWidget(QLabel("Activity log"))
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(170); outer.addWidget(self.log)
        self.statusBar().showMessage("Ready")
        self.update_options()
        self.apply_theme(self.dark.isChecked())

    def choose_source(self):
        value = QFileDialog.getExistingDirectory(self,"Select source",self.source.text())
        if value: self.source.setText(value); self.settings.setValue("paths/source", value)

    def choose_output(self):
        value = QFileDialog.getExistingDirectory(self,"Select output",self.source.text())
        if value: self.output.setText(value); self.settings.setValue("paths/output", value)

    def choose_config(self):
        value, _ = QFileDialog.getOpenFileName(self,"Select values file", "", "Configuration (*.toml *.json *.ini *.cfg)")
        if value: self.config.setText(value); self.edit_config()

    def update_options(self, *_):
        action = self.action.currentText()
        self.config.setEnabled(action != "organize")
        self.modify_fields_button.setEnabled(action != "organize")
        self.in_place.setEnabled(action == "organize")
        if action != "organize": self.in_place.setChecked(False)
        in_place = self.in_place.isChecked()
        for widget in (self.layout,self.rename,self.extension,self.overwrite,self.output):
            widget.setEnabled(not in_place)
        if in_place: self.dicomdir.setChecked(True)

    def source_path(self):
        path = Path(self.source.text()).expanduser()
        if not path.is_dir(): raise ValueError("Select an existing source directory")
        return path

    def start(self, args, done=None):
        if self.proc is not None:
            QMessageBox.warning(self,"Busy","Another operation is running")
            return
        self.log.appendPlainText("$ dicom-manager " + " ".join(args))
        self.proc = QProcess(self)
        self.proc.setProgram(sys.executable)
        self.proc.setArguments(["-m", "dicom_manager", *args])
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(lambda: self.log.appendPlainText(bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace").rstrip("\n")))
        self.proc.finished.connect(lambda code, status: self.finished(code, done))
        self.proc.start(); self.statusBar().showMessage("Running…")

    def finished(self, code, done):
        self.statusBar().showMessage("Completed" if code == 0 else f"Failed (exit {code})")
        self.log.appendPlainText(f"Exit code: {code}\n")
        self.proc.deleteLater(); self.proc = None
        if done and code == 0: done()

    def _set_table(self, headers, rows):
        self.table.setSortingEnabled(False)
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))
        for r, values in enumerate(rows):
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                self.table.setItem(r, c, item)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.resizeColumnsToContents()

    def inspect_files(self):
        try:
            source = self.source_path()
            if not self.inspect_selected:
                raise ValueError("Select at least one DICOM field")
            from .core.discovery import locate_dicom_files
            import pydicom
            files = locate_dicom_files(source)
            fields = self.inspect_selected
            datasets = [(path, pydicom.dcmread(path, stop_before_pixels=True)) for path in files]
            mode = self.presentation.currentText()
            if mode == "Auto":
                # Prefer multi-file only when estimated table width fits the viewport.
                estimated = 190 + sum(max(130, len(f) * 9) for f in fields)
                mode = "Multi-file" if estimated <= self.table.viewport().width() else "Per-file"
            if mode == "Multi-file":
                rows = [[str(path.relative_to(source)), *(str(getattr(ds, f, "")) for f in fields)]
                        for path, ds in datasets]
                self._set_table(["File", *fields], rows)
            else:
                rows = []
                for path, ds in datasets:
                    name = str(path.relative_to(source))
                    rows.extend([[name, field, str(getattr(ds, field, ""))] for field in fields])
                self._set_table(["File", "Field", "Value"], rows)
            self.statusBar().showMessage(f"Inspected {len(files)} files — {mode.lower()} (scroll for complete values)")
        except Exception as exc:
            QMessageBox.warning(self, "Inspect", str(exc))

    def inspect_fileset(self):
        try:
            source = self.source_path()
            from .core.fileset import inspect_fileset
            report = inspect_fileset(source)
            rows = [
                ["DICOM files", report.files],
                ["DICOMDIR present", "Yes" if report.dicomdir_present else "No"],
                ["File ID compliant", "Yes" if report.compliant else "No"],
                ["Non-compliant directories", len(report.invalid_directories)],
                ["Non-compliant files", len(report.invalid_files)],
            ]
            if report.invalid_directories:
                rows.append(["Non-compliant directories — examples", ""])
                rows.extend([["Directory", str(p)] for p in report.invalid_directories])
            if report.invalid_files:
                rows.append(["Non-compliant files — examples", ""])
                rows.extend([["File", str(p)] for p in report.invalid_files])
            if not report.compliant:
                rows.append(["Recommendation", "Use --rename and/or --hierarchical before --dicomdir"])
            self._set_table(["Property", "Value"], rows)
            self.log.appendPlainText(f"File-set inspected: {source} ({report.files} files, compliant={report.compliant})")
            self.statusBar().showMessage("File-set inspection complete")
        except Exception as exc:
            QMessageBox.warning(self, "Inspect File-set", str(exc))

    def run_operation(self):
        try: source = self.source_path()
        except ValueError as exc: QMessageBox.warning(self,"Source",str(exc)); return
        action = self.action.currentText()
        if self.dicomdir.isChecked() and self.extension.isChecked():
            QMessageBox.warning(self,"Incompatible options","DICOMDIR cannot reference .dcm extensions."); return
        args = [action,"-d",str(source)]
        if self.in_place.isChecked():
            args.extend(["--in-place","--dicomdir"])
        else:
            if self.output.text().strip(): args.extend(["-o",self.output.text().strip()])
            if self.layout.currentText() != "preserve": args.append("--"+self.layout.currentText())
            for widget, flag in ((self.rename,"--rename"),(self.extension,"--dcm-extension"),
                                 (self.dicomdir,"--dicomdir"),(self.overwrite,"--overwrite")):
                if widget.isChecked(): args.append(flag)
        if action != "organize":
            if self.config.text().strip(): args.extend(["--from-file",self.config.text().strip()])
            if action in ("modify", "anonymize"):
                for keyword, value in (self.modify_selected if action == "modify" else self.anonymize_selected).items():
                    args.extend(["--set", f"{keyword}={value}"])
            if action == "modify" and not self.config.text().strip() and not self.modify_selected:
                QMessageBox.warning(self,"Missing values","Modify requires a values file or KEY=VALUE"); return
        if action in ("modify", "anonymize") and not self.confirm_scope(source, action): return
        if self.overwrite.isChecked() and not self.in_place.isChecked():
            answer = QMessageBox.question(self,"Confirm overwrite","Replace the existing output directory if present?")
            if answer != QMessageBox.StandardButton.Yes: return
        self.start(args)

    def refresh_field_counts(self):
        self.inspect_field_count.setText(f"{len(self.inspect_selected)} selected")
        if hasattr(self, "modify_field_count"):
            self.modify_field_count.setText(f"{len(self.anonymize_selected) if self.action.currentText() == 'anonymize' else len(self.modify_selected)} selected")

    def choose_inspect_fields(self):
        dialog = FieldsDialog(self, dict.fromkeys(self.inspect_selected, ""))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.inspect_selected = dialog.selection()
            self.refresh_field_counts()

    def existing_values(self, source):
        values = {}
        try:
            paths = locate_dicom_files(source)
            # Scan all instances; do not present an arbitrary first value as representative.
            for path in paths:
                ds = pydicom.dcmread(path, stop_before_pixels=True)
                for key in COMMON:
                    value = str(getattr(ds, key, ""))
                    if key not in values: values[key] = value
                    elif values[key] != value: values[key] = "<multiple values>"
        except (OSError, ValueError, pydicom.errors.InvalidDicomError):
            return {}
        return values

    def choose_modify_fields(self):
        action = self.action.currentText()
        selected = self.anonymize_selected if action == "anonymize" else self.modify_selected
        allowed = set(ANONYMIZE_DEFAULTS) if action == "anonymize" else None
        existing = self.existing_values(self.source_path())
        dialog = FieldsDialog(self, selected, modify=True, allowed=allowed, existing=existing)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = dialog.selection()
            # An unedited mixed-value placeholder must never be written to a DICOM file.
            if any(v == "<multiple values>" for v in result.values()):
                QMessageBox.warning(self, "Multiple values", "Replace <multiple values> with an explicit value before applying.")
                return
            if action == "anonymize": self.anonymize_selected = result
            else: self.modify_selected = result
            self.refresh_field_counts()

    def edit_config(self):
        path = Path(self.config.text().strip())
        if not path.is_file():
            QMessageBox.warning(self, "Values file", "Select an existing values file first.")
            return
        try: values = load_values(path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Values file", str(exc)); return
        allowed = set(ANONYMIZE_DEFAULTS) if self.action.currentText() == "anonymize" else None
        if allowed is not None and set(values) - allowed:
            QMessageBox.warning(self, "Values file", "The file contains unsupported anonymization fields."); return
        dialog = FieldsDialog(self, values, modify=True, allowed=allowed)
        if dialog.exec() != QDialog.DialogCode.Accepted: return
        output, _ = QFileDialog.getSaveFileName(self, "Save edited values as", str(path.with_name(path.stem + "-edited" + path.suffix)), "Configuration (*.toml *.json *.ini)")
        if not output: return
        try:
            write_template(Path(output), dialog.selection())
            self.config.setText(output)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Save values", str(exc))

    def confirm_scope(self, source, action):
        from collections import defaultdict
        fields = self.anonymize_selected if action == "anonymize" else self.modify_selected
        if self.config.text().strip():
            try: fields = {**load_values(Path(self.config.text().strip())), **fields}
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, "Values file", str(exc)); return False
        if action == "anonymize": fields = {**ANONYMIZE_DEFAULTS, **fields}
        if not fields: return True
        counts = [set(), set(), set()]
        files = locate_dicom_files(source)
        for path in files:
            ds = pydicom.dcmread(path, stop_before_pixels=True)
            patient = str(getattr(ds, "PatientID", "")) or str(getattr(ds, "PatientName", ""))
            study = str(getattr(ds, "StudyInstanceUID", ""))
            series = str(getattr(ds, "SeriesInstanceUID", ""))
            counts[0].add(patient); counts[1].add((patient,study)); counts[2].add((patient,study,series))
        risky = (("PatientName", "PatientID", "PatientBirthDate"), ("StudyDescription", "StudyDate", "StudyID", "AccessionNumber"), ("SeriesDescription", "SeriesNumber", "Modality"))
        alerts = [f"{len(counts[i])} distinct {label} affected by {', '.join(sorted(set(fields) & set(keys)))}" for i,(keys,label) in enumerate(zip(risky,("patients", "studies", "series"))) if len(counts[i]) > 1 and set(fields) & set(keys)]
        if alerts:
            message = (f"This operation targets all {len(files)} DICOM instances.\n\n" + "\n".join(alerts) + "\n\nApply these changes to ALL selected instances?")
            return QMessageBox.question(self, "Multiple-patient/study/series warning", message) == QMessageBox.StandardButton.Yes
        return True

    def choose_template_path(self):
        kind = self.template_kind.currentText()
        extension = self.template_format.currentText()
        path, _ = QFileDialog.getSaveFileName(self, "Save template", str(Path.home() / f"{kind}.{extension}"), "All files (*)")
        if path: self.template_path.setText(path)

    def generate_template(self):
        path = self.template_path.text().strip()
        if not path:
            QMessageBox.warning(self, "Template", "Select a destination file first")
            return
        if Path(path).exists():
            answer = QMessageBox.question(self, "Replace template?", f"Overwrite {path}?")
            if answer != QMessageBox.StandardButton.Yes: return
        self.start(["template", self.template_kind.currentText(), "--format", self.template_format.currentText(), "--output", path])

    def show_about(self):
        """Show release details and copyable diagnostics without patient information."""
        dialog = QDialog(self)
        dialog.setWindowTitle("About DICOM-Manager")
        dialog.setMinimumWidth(460)
        layout = QVBoxLayout(dialog)
        heading = QLabel("DICOM-Manager")
        heading.setStyleSheet("font-size: 23px; font-weight: 700;")
        layout.addWidget(heading)
        layout.addWidget(QLabel(f"Version {APP_VERSION}"))
        layout.addWidget(QLabel("DICOM metadata and file-set management"))
        layout.addWidget(QLabel("Developer: Pascal Malouin (EGOUID0)"))
        layout.addWidget(QLabel("License: MIT · Copyright © 2026 Pascal Malouin"))
        diagnostics = (
            f"DICOM-Manager: {APP_VERSION}\n"
            f"Python: {platform.python_version()}\n"
            f"PySide6: {pyside_version}\n"
            f"Qt: {qVersion()}\n"
            f"pydicom: {pydicom.__version__}\n"
            f"OS: {platform.system()} {platform.release()} ({platform.machine()})"
        )
        details = QPlainTextEdit(diagnostics)
        details.setReadOnly(True)
        details.setMinimumHeight(120)
        layout.addWidget(details)
        actions = QHBoxLayout()
        github = QPushButton("GitHub")
        github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/EGOUID0/DICOM-Manager/")))
        actions.addWidget(github)
        copy = QPushButton("Copy system information")
        copy.clicked.connect(lambda: QApplication.clipboard().setText(diagnostics))
        actions.addWidget(copy)
        close = QPushButton("Close")
        close.clicked.connect(dialog.accept)
        actions.addWidget(close)
        layout.addLayout(actions)
        dialog.exec()

    def closeEvent(self, event):
        self.settings.setValue("inspect/fields", self.inspect_selected)
        self.settings.setValue("paths/source", self.source.text())
        self.settings.setValue("paths/output", self.output.text())
        super().closeEvent(event)

    def apply_theme(self, dark):
        app = QApplication.instance()
        self.settings.setValue("appearance/dark_mode", dark)
        app.setStyle("Fusion")
        if dark:
            bg, surface, input_bg, fg, border, accent, hover, alt = (
                "#20242b", "#292f39", "#151920", "#e6e9ef", "#4c5563", "#426da5", "#3b4656", "#1b2028")
        else:
            bg, surface, input_bg, fg, border, accent, hover, alt = (
                "#f1f3f6", "#ffffff", "#ffffff", "#202833", "#bac3cf", "#426da5", "#e0e8f2", "#e9edf3")
        app.setStyleSheet(f"""
            QWidget {{ background: {bg}; color: {fg}; }}
            QGroupBox {{ border: 1px solid {border}; border-radius: 5px; margin-top: 12px; padding: 8px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
            QLineEdit, QPlainTextEdit, QTableWidget, QComboBox, QScrollArea {{
                background: {input_bg}; color: {fg}; border: 1px solid {border};
                selection-background-color: {accent}; selection-color: white;
            }}
            QPushButton {{ background: {surface}; color: {fg}; border: 1px solid {border};
                border-radius: 4px; padding: 6px 12px; }}
            QPushButton:hover {{ background: {hover}; }}
            QPushButton:disabled {{ color: #858d99; }}
            QTabWidget::pane {{ border: 1px solid {border}; }}
            QTabBar::tab {{ background: {surface}; color: {fg}; border: 1px solid {border};
                padding: 8px 17px; }}
            QTabBar::tab:selected {{ background: {accent}; color: white; }}
            QHeaderView::section {{ background: {surface}; color: {fg};
                border: 1px solid {border}; padding: 5px; }}
            QTableWidget {{ alternate-background-color: {alt}; gridline-color: {border}; }}
            QStatusBar {{ border-top: 1px solid {border}; }}
        """)


def main():
    app = QApplication(sys.argv)
    window = Window(); window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
