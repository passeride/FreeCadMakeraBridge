# -*- coding: utf-8 -*-
"""Klargjør på Z1: export one CAM Machine job and open it in OpenSpindle."""
from pathlib import Path
import sys

from . import bridge, cam


def run():
    import FreeCAD as App
    from PySide import QtWidgets, QtCore, QtGui
    title = "Klargjør på Z1 · OpenSpindle"
    try:
        job = cam.get_job()
        prefs = App.ParamGet("User parameter:BaseApp/Preferences/Macro/SendToOpenSpindle")
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle(title)
        layout = QtWidgets.QFormLayout(dialog)
        layout.addRow("CAM-jobb:", QtWidgets.QLabel(job.Label))
        executable = QtWidgets.QLineEdit(prefs.GetString("Executable", ""))
        browse = QtWidgets.QPushButton("Finn installasjon…")
        def choose():
            detected = bridge.discover_receiver()
            if detected:
                executable.setText(detected)
                return detected
            if sys.platform == 'darwin':
                path = QtWidgets.QFileDialog.getExistingDirectory(dialog, "Velg OpenSpindle.app")
            else:
                path, _ = QtWidgets.QFileDialog.getOpenFileName(dialog, "Velg OpenSpindle-programfil")
            if path:
                executable.setText(path)
            return path
        browse.clicked.connect(choose)
        app_row = QtWidgets.QHBoxLayout()
        app_row.addWidget(executable)
        app_row.addWidget(browse)
        layout.addRow("OpenSpindle:", app_row)
        folder = QtWidgets.QLineEdit(prefs.GetString("Exports", str(Path.home() / "Documents" / "FreeCAD-OpenSpindle")))
        layout.addRow("Eksportmappe:", folder)
        opening = QtWidgets.QCheckBox("Åpne eksporten i OpenSpindle")
        opening.setChecked(True)
        layout.addRow(opening)
        note = QtWidgets.QLabel("G-koden åpnes for kontroll. Oppsett, nullpunkt og verktøy må bekreftes i OpenSpindle.\n"
                               "Import og maskinoverføring bekreftes ikke av denne makroen.\n"
                               "En kilde-ID lagres som egenskap på CAM-jobben; lagre dokumentet for å beholde den.")
        note.setWordWrap(True)
        layout.addRow(note)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.button(QtWidgets.QDialogButtonBox.Ok).setText("Klargjør på Z1")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not folder.text().strip():
            raise ValueError("Velg en eksportmappe.")
        def decide(reason):
            prompt = QtWidgets.QMessageBox(dialog)
            prompt.setWindowTitle("OpenSpindle er ikke tilgjengelig")
            prompt.setText(reason)
            prompt.setInformativeText("Finn programmet, åpne den offisielle nedlastingssiden eller eksporter bare fil. "
                                      "Nedlastingssiden installerer ikke programmet automatisk."
                                      + (" På Linux finnes det foreløpig ingen offisiell installasjonspakke." if sys.platform.startswith("linux") else ""))
            find_button = prompt.addButton("Finn installasjon", QtWidgets.QMessageBox.ActionRole)
            download_button = prompt.addButton("Åpne nedlastingsside", QtWidgets.QMessageBox.ActionRole)
            export_button = prompt.addButton("Eksporter bare fil", QtWidgets.QMessageBox.AcceptRole)
            prompt.addButton(QtWidgets.QMessageBox.Cancel)
            prompt.exec_()
            return {find_button: 'find', download_button: 'download', export_button: 'export'}.get(prompt.clickedButton(), 'cancel')
        def download(url):
            if not QtGui.QDesktopServices.openUrl(QtCore.QUrl(url)):
                QtWidgets.QMessageBox.warning(dialog, title, "Kunne ikke åpne nettleseren. Åpne: " + url)
        receiver = bridge.configure_receiver(executable.text().strip(), opening.isChecked(), decide, choose, download)
        if receiver is None:
            return
        app_path, should_open = receiver
        executable.setText(app_path)
        bridge.check_job(job)
        gcode, post = cam.postprocess(job)
        bridge.check_job(job)
        source = bridge.source_metadata(job, post, App.Version())
        path, manifest = bridge.publish(folder.text().strip(), gcode, source)
        prefs.SetString("Executable", executable.text().strip())
        prefs.SetString("Exports", folder.text().strip())
        message = "Eksportert lokalt: %s\nRevisjon: %s" % (path, manifest["program"]["sha256"][:12])
        if should_open:
            try:
                bridge.launch(executable.text().strip(), path)
                message += "\nÅpning forespurt. Kontroller importen i OpenSpindle."
            except Exception as exc:
                QtWidgets.QMessageBox.warning(dialog, title, message + "\nKunne ikke åpne OpenSpindle: %s\nÅpne .nc-filen manuelt." % exc)
                return
        QtWidgets.QMessageBox.information(dialog, title, message)
    except Exception as exc:
        App.Console.PrintError("OpenSpindle: %s\n" % exc)
        QtWidgets.QMessageBox.critical(None, title, str(exc))
