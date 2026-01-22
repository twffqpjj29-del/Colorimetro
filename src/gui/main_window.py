# src/gui/main_window.py
from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.color import rgb_to_hex
from core.colorimetry import describe_pipeline
from core.export_pdf import export_pdf
from core.munsell import closest_munsell_real_with_de
from core.report_model import ReportState
from core.sampling import sample_rgb_and_std
from core.version import APP_AUTHOR, APP_COPYRIGHT, APP_NAME, APP_VERSION, ASCII_LOGO
from gui.help_dialog import HelpDialog, load_text_file
from gui.image_view import ImageView


def _isfinite(x: float) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} (Desktop)")
        self.resize(1320, 820)

        self.state = ReportState()

        # ---------------- Image viewer ----------------
        self.viewer = ImageView()
        self.viewer.sample_requested.connect(self.on_sample_requested)

        # ---------------- Controls ----------------
        self.spot_size = QSpinBox()
        self.spot_size.setRange(1, 401)
        self.spot_size.setSingleStep(2)
        self.spot_size.setValue(31)
        self.spot_size.valueChanged.connect(self.viewer.set_spot_size)

        self.mode = QComboBox()
        self.mode.addItems(["exact", "average", "weighted"])
        self.mode.currentTextChanged.connect(self.viewer.set_mode)

        self.de_method = QComboBox()
        self.de_method.addItems(["DE2000", "CIE76"])

        # ---------------- Last sample ----------------
        self.rgb_label = QLabel("-")
        self.std_label = QLabel("-")  # σRGB
        self.hex_label = QLabel("-")
        self.munsell_label = QLabel("-")
        self.match_de_label = QLabel("-")  # ΔE minimo del match Munsell

        # ---------------- Notes ----------------
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Note...")
        self.notes.textChanged.connect(self._sync_notes)

        # ---------------- Table ----------------
        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(
            ["#", "X", "Y", "Spot", "Mode", "ΔE method", "RGB", "σRGB", "HEX", "Munsell", "Match ΔE"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)

        # ---------------- Right panel ----------------
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setAlignment(Qt.AlignTop)
        right_l.setContentsMargins(8, 8, 8, 8)
        right_l.setSpacing(8)

        box_controls = QGroupBox("Controlli")
        form = QFormLayout(box_controls)
        form.setContentsMargins(8, 8, 8, 8)
        form.setSpacing(6)
        form.addRow("Spot (px)", self.spot_size)
        form.addRow("Mode", self.mode)
        form.addRow("ΔE method", self.de_method)
        right_l.addWidget(box_controls)

        box_values = QGroupBox("Ultimo campione")
        vform = QFormLayout(box_values)
        vform.setContentsMargins(8, 8, 8, 8)
        vform.setSpacing(6)
        vform.addRow("RGB", self.rgb_label)
        vform.addRow("σRGB", self.std_label)
        vform.addRow("HEX", self.hex_label)
        vform.addRow("Munsell", self.munsell_label)
        vform.addRow("Match ΔE", self.match_de_label)
        right_l.addWidget(box_values)

        box_samples = QGroupBox("Campioni")
        sl = QVBoxLayout(box_samples)
        sl.setContentsMargins(8, 8, 8, 8)
        sl.setSpacing(6)
        sl.addWidget(self.table)
        right_l.addWidget(box_samples, 1)

        box_notes = QGroupBox("Note")
        nl = QVBoxLayout(box_notes)
        nl.setContentsMargins(8, 8, 8, 8)
        nl.setSpacing(6)
        nl.addWidget(self.notes)
        right_l.addWidget(box_notes)

        # ---------------- Splitter ----------------
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.viewer)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 2)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, True)

        root = QWidget()
        root_l = QHBoxLayout(root)
        root_l.setContentsMargins(0, 0, 0, 0)
        root_l.addWidget(splitter)
        self.setCentralWidget(root)

        # init viewer state
        self.viewer.set_spot_size(self.spot_size.value())
        self.viewer.set_mode(self.mode.currentText())

        # ---------------- Status bar ----------------
        self.statusBar().showMessage("Ready")

        # ---------------- Toolbar (Open first) ----------------
        tb = QToolBar("Comandi")
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(Qt.TopToolBarArea, tb)

        act_open = QAction("Apri", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self.open_image)
        tb.addAction(act_open)  # OPEN FIRST

        act_export = QAction("Esporta PDF", self)
        act_export.setShortcut(QKeySequence("Ctrl+E"))
        act_export.triggered.connect(self.export_pdf_dialog)
        tb.addAction(act_export)

        tb.addSeparator()

        act_undo = QAction("Undo", self)
        act_undo.setShortcut(QKeySequence("U"))
        act_undo.triggered.connect(self.undo_last_sample)
        tb.addAction(act_undo)

        act_remove = QAction("Rimuovi", self)
        act_remove.setShortcut(QKeySequence.Delete)
        act_remove.triggered.connect(self.remove_selected_sample)
        tb.addAction(act_remove)

        act_clear = QAction("Svuota", self)
        act_clear.setShortcut(QKeySequence("Ctrl+L"))
        act_clear.triggered.connect(self.clear_samples)
        tb.addAction(act_clear)

        tb.addSeparator()

        act_fit = QAction("Fit", self)
        act_fit.setShortcut(QKeySequence("F"))
        act_fit.triggered.connect(self.viewer.fit_to_window)
        tb.addAction(act_fit)

        act_zoom_in = QAction("Zoom +", self)
        act_zoom_in.setShortcuts([QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")])
        act_zoom_in.triggered.connect(self.viewer.zoom_in)
        tb.addAction(act_zoom_in)

        act_zoom_out = QAction("Zoom −", self)
        act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        act_zoom_out.triggered.connect(self.viewer.zoom_out)
        tb.addAction(act_zoom_out)

        act_reset = QAction("Reset view", self)
        act_reset.setShortcut(QKeySequence("R"))
        act_reset.triggered.connect(self.viewer.reset_view)
        tb.addAction(act_reset)

        tb.addSeparator()

        act_toggle_de = QAction("ΔE", self)
        act_toggle_de.setShortcut(QKeySequence("D"))
        act_toggle_de.triggered.connect(self._toggle_de_method)
        tb.addAction(act_toggle_de)

        act_toggle_mode = QAction("Mode", self)
        act_toggle_mode.setShortcut(QKeySequence("M"))
        act_toggle_mode.triggered.connect(self._toggle_mode)
        tb.addAction(act_toggle_mode)

        act_spot_minus = QAction("Spot −", self)
        act_spot_minus.setShortcut(QKeySequence("["))
        act_spot_minus.triggered.connect(lambda: self._bump_spot(-2))
        tb.addAction(act_spot_minus)

        act_spot_plus = QAction("Spot +", self)
        act_spot_plus.setShortcut(QKeySequence("]"))
        act_spot_plus.triggered.connect(lambda: self._bump_spot(+2))
        tb.addAction(act_spot_plus)

        tb.addSeparator()

        act_help = QAction("Guida", self)
        act_help.setShortcut(QKeySequence("F1"))
        act_help.triggered.connect(self.show_help)
        tb.addAction(act_help)

        act_about = QAction("Info", self)
        act_about.triggered.connect(self.show_about)
        tb.addAction(act_about)

        # Allow shortcuts even if focus is elsewhere
        for a in (
            act_open,
            act_export,
            act_undo,
            act_remove,
            act_clear,
            act_fit,
            act_zoom_in,
            act_zoom_out,
            act_reset,
            act_toggle_de,
            act_toggle_mode,
            act_spot_minus,
            act_spot_plus,
            act_help,
            act_about,
        ):
            self.addAction(a)

        # ---------------- Menu bar: Help ----------------
        m_help = self.menuBar().addMenu("Aiuto")
        m_help.addAction(act_help)

        act_help_ext = QAction("Apri guida (esterno)", self)
        act_help_ext.triggered.connect(self.open_help_external)
        m_help.addAction(act_help_ext)

        m_help.addSeparator()
        m_help.addAction(act_about)

    # ---------------- Paths / Help ----------------
    def _project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def _help_path(self) -> Path:
        return self._project_root() / "assets" / "help" / "README.txt"

    def show_help(self) -> None:
        p = self._help_path()
        if not p.exists():
            QMessageBox.warning(self, "Guida", f"File guida non trovato:\n{p}")
            return
        dlg = HelpDialog(f"Guida – {APP_NAME}", load_text_file(p), parent=self)
        dlg.exec()

    def open_help_external(self) -> None:
        p = self._help_path()
        if not p.exists():
            QMessageBox.warning(self, "Guida", f"File guida non trovato:\n{p}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    def show_about(self) -> None:
        pipeline = describe_pipeline()
        about = (
            f"{ASCII_LOGO}\n"
            f"{APP_NAME}  v{APP_VERSION}\n"
            f"{'-' * 60}\n"
            f"{pipeline}\n"
            f"{'-' * 60}\n"
            f"Author: {APP_AUTHOR}\n"
            f"{APP_COPYRIGHT}\n"
        )
        dlg = HelpDialog(f"Informazioni – {APP_NAME}", about, parent=self)
        dlg.exec()

    # ---------------- UI helpers ----------------
    def _sync_notes(self) -> None:
        self.state.notes = self.notes.toPlainText()

    def _toggle_de_method(self) -> None:
        i = self.de_method.currentIndex()
        self.de_method.setCurrentIndex((i + 1) % self.de_method.count())
        self.statusBar().showMessage(f"ΔE method: {self.de_method.currentText()}", 1500)

    def _toggle_mode(self) -> None:
        i = self.mode.currentIndex()
        self.mode.setCurrentIndex((i + 1) % self.mode.count())
        self.statusBar().showMessage(f"Mode: {self.mode.currentText()}", 1500)

    def _bump_spot(self, delta: int) -> None:
        v = self.spot_size.value() + int(delta)
        # mantieni dispari per simmetria spot (opzionale ma consigliato)
        if v % 2 == 0:
            v += 1 if delta >= 0 else -1
        v = max(self.spot_size.minimum(), min(self.spot_size.maximum(), v))
        self.spot_size.setValue(v)
        self.statusBar().showMessage(f"Spot: {v}px", 1200)

    # ---------------- File actions ----------------
    def open_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleziona immagine",
            "",
            "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp);;All files (*.*)",
        )
        if not path:
            return

        self.viewer.load_image(path)
        self.state.image_path = path

        self.state.clear_samples()
        self._refresh_table()
        self._reset_last_labels()

        self.statusBar().showMessage(f"Loaded image: {path}", 3000)

    # ---------------- Sampling ----------------
    def on_sample_requested(self, x_img: int, y_img: int, spot: int, mode: str) -> None:
        if self.viewer.image_array is None:
            return

        rgb, rgb_std = sample_rgb_and_std(self.viewer.image_array, x_img, y_img, spot, mode)
        hx = rgb_to_hex(*rgb)
        de_method = self.de_method.currentText().strip()

        try:
            munsell, de_min = closest_munsell_real_with_de(rgb, method=de_method)
        except Exception as e:
            QMessageBox.warning(self, "Munsell", f"Impossibile calcolare Munsell ({de_method}).\n{e}")
            munsell, de_min = "-", float("nan")

        self.rgb_label.setText(f"{rgb[0]}, {rgb[1]}, {rgb[2]}")
        self.std_label.setText(f"{rgb_std[0]:.1f}, {rgb_std[1]:.1f}, {rgb_std[2]:.1f}")
        self.hex_label.setText(hx)
        self.munsell_label.setText(munsell)
        self.match_de_label.setText("-" if not _isfinite(de_min) else f"{de_min:.2f}")

        # NB: questa firma richiede report_model.Sample con rgb_std e munsell_de
        self.state.add_sample(
            x=x_img,
            y=y_img,
            spot=spot,
            mode=mode,
            de_method=de_method,
            rgb=rgb,
            rgb_std=rgb_std,
            hex_code=hx,
            munsell=munsell,
            munsell_de=de_min if _isfinite(de_min) else float("nan"),
        )

        self._refresh_table()
        self.table.selectRow(self.table.rowCount() - 1)
        self.statusBar().showMessage(f"Added sample #{self.state.samples[-1].idx}", 2000)

    # ---------------- Table / state ----------------
    def _refresh_table(self) -> None:
        self.table.setRowCount(len(self.state.samples))
        for r, s in enumerate(self.state.samples):
            self.table.setItem(r, 0, QTableWidgetItem(str(s.idx)))
            self.table.setItem(r, 1, QTableWidgetItem(str(s.x)))
            self.table.setItem(r, 2, QTableWidgetItem(str(s.y)))
            self.table.setItem(r, 3, QTableWidgetItem(str(s.spot)))
            self.table.setItem(r, 4, QTableWidgetItem(s.mode))
            self.table.setItem(r, 5, QTableWidgetItem(s.de_method))
            self.table.setItem(r, 6, QTableWidgetItem(f"{s.rgb[0]},{s.rgb[1]},{s.rgb[2]}"))
            self.table.setItem(r, 7, QTableWidgetItem(f"{s.rgb_std[0]:.1f},{s.rgb_std[1]:.1f},{s.rgb_std[2]:.1f}"))
            self.table.setItem(r, 8, QTableWidgetItem(s.hex))
            self.table.setItem(r, 9, QTableWidgetItem(s.munsell))
            self.table.setItem(r, 10, QTableWidgetItem("-" if not _isfinite(s.munsell_de) else f"{s.munsell_de:.2f}"))

    def _reset_last_labels(self) -> None:
        self.rgb_label.setText("-")
        self.std_label.setText("-")
        self.hex_label.setText("-")
        self.munsell_label.setText("-")
        self.match_de_label.setText("-")

    def _refresh_last_labels(self) -> None:
        if self.state.samples:
            s = self.state.samples[-1]
            self.rgb_label.setText(f"{s.rgb[0]}, {s.rgb[1]}, {s.rgb[2]}")
            self.std_label.setText(f"{s.rgb_std[0]:.1f}, {s.rgb_std[1]:.1f}, {s.rgb_std[2]:.1f}")
            self.hex_label.setText(s.hex)
            self.munsell_label.setText(s.munsell)
            self.match_de_label.setText("-" if not _isfinite(s.munsell_de) else f"{s.munsell_de:.2f}")
        else:
            self._reset_last_labels()

    def remove_selected_sample(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            self.statusBar().showMessage("No row selected", 1500)
            return
        idx = self.state.samples[row].idx
        self.state.remove_sample_by_idx(idx)
        self._refresh_table()
        self.statusBar().showMessage(f"Removed sample #{idx}", 2000)
        self._refresh_last_labels()

    def undo_last_sample(self) -> None:
        if not self.state.samples:
            self.statusBar().showMessage("No samples to undo", 2000)
            return
        last_idx = self.state.samples[-1].idx
        self.state.remove_sample_by_idx(last_idx)
        self._refresh_table()
        self.statusBar().showMessage(f"Removed sample #{last_idx}", 2000)
        self._refresh_last_labels()

    def clear_samples(self) -> None:
        self.state.clear_samples()
        self._refresh_table()
        self.statusBar().showMessage("Samples cleared", 2000)
        self._refresh_last_labels()

    # ---------------- Export ----------------
    def export_pdf_dialog(self) -> None:
        if not self.state.image_path:
            QMessageBox.warning(self, "Export PDF", "Carica prima un’immagine.")
            return
        if not self.state.samples:
            QMessageBox.warning(self, "Export PDF", "Nessun campione presente.")
            return

        out, _ = QFileDialog.getSaveFileName(self, "Salva PDF", "", "PDF (*.pdf)")
        if not out:
            return
        if not out.lower().endswith(".pdf"):
            out += ".pdf"

        try:
            export_pdf(out, self.state, title=f"{APP_NAME} Report")
        except Exception as e:
            QMessageBox.critical(self, "Export PDF", f"Errore durante l’export:\n{e}")
            return

        QMessageBox.information(self, "Export PDF", "PDF esportato correttamente.")
        self.statusBar().showMessage(f"Exported PDF: {out}", 4000)