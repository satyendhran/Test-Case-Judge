import sys
import os
import subprocess
import time
import tempfile
from pathlib import Path
from functools import partial

from PyQt5.QtCore import (
    Qt,
    QSize,
    QTimer,
    QUrl,
    QThreadPool,
    QRunnable,
    pyqtSignal,
    QObject,
    QPropertyAnimation,
    QEasingCurve,
)
from PyQt5.QtGui import QIcon, QFont, QDragEnterEvent, QDropEvent, QPalette, QColor
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QMessageBox,
    QHeaderView,
    QProgressBar,
    QToolBar,
    QAction,
    QSplitter,
    QDockWidget,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
)

import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)


class Signals(QObject):
    finished = pyqtSignal(int, dict)
    log = pyqtSignal(str)
    progress = pyqtSignal(int)


class RunTask(QRunnable):
    def __init__(self, idx, cmd, inp_path, ans_path, timeout=2):
        super().__init__()
        self.idx = idx
        self.cmd = cmd
        self.inp_path = inp_path
        self.ans_path = ans_path
        self.timeout = timeout
        self.signals = Signals()

    def run(self):
        try:
            with open(self.inp_path, "r") as f:
                start = time.perf_counter()
                proc = subprocess.run(
                    self.cmd,
                    stdin=f,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=self.timeout,
                )
                end = time.perf_counter()
            elapsed = end - start
        except subprocess.TimeoutExpired:
            res = {
                "status": "TLE",
                "stdout": "",
                "stderr": "Time Limit Exceeded",
                "time": self.timeout,
            }
            self.signals.log.emit(f"Test {self.idx + 1}: TLE")
            self.signals.finished.emit(self.idx, res)
            return

        if proc.returncode != 0:
            res = {
                "status": "RE",
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "time": elapsed,
            }
            self.signals.log.emit(f"Test {self.idx + 1}: Runtime Error")
            self.signals.finished.emit(self.idx, res)
            return

        expected = Path(self.ans_path).read_text().strip()
        got = proc.stdout.strip()
        status = "Accepted" if got == expected else "Wrong Answer"
        diff = self._make_diff(expected, got)
        res = {
            "status": status,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "diff": diff,
            "time": elapsed,
        }
        self.signals.log.emit(f"Test {self.idx + 1}: {status} ({elapsed:.3f}s)")
        self.signals.finished.emit(self.idx, res)

    def _make_diff(self, exp, got):
        e_lines, g_lines = exp.splitlines(), got.splitlines()
        out = []
        for i in range(max(len(e_lines), len(g_lines))):
            e = e_lines[i] if i < len(e_lines) else "<none>"
            g = g_lines[i] if i < len(g_lines) else "<none>"
            if e != g:
                out.append(f"Line {i + 1}: Expected [{e}] Got [{g}]")
        return "\n".join(out) or "Outputs match exactly."


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Case Judge")
        self.resize(1200, 720)
        self._setup_palette()
        self.solution = None
        self.exec_path = None
        self.testcases = []
        self.results = []
        self.threadpool = QThreadPool.globalInstance()
        self._init_ui()

    def _setup_palette(self):
        p = QPalette()
        p.setColor(QPalette.Window, QColor("#0f1724"))
        p.setColor(QPalette.Base, QColor("#071022"))
        p.setColor(QPalette.AlternateBase, QColor("#0b1220"))
        p.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
        p.setColor(QPalette.WindowText, QColor("#d9f0ff"))
        p.setColor(QPalette.Text, QColor("#e6f7ff"))
        p.setColor(QPalette.Button, QColor("#0f1724"))
        p.setColor(QPalette.ButtonText, QColor("#aee1ff"))
        self.setPalette(p)
        font = QFont("Segoe UI", 10)
        self.setFont(font)

    def _init_ui(self):
        central = QWidget()
        main_layout = QVBoxLayout()
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))

        act_select = QAction(QIcon.fromTheme("document-open"), "Select Solution", self)
        act_select.triggered.connect(self.select_solution)
        toolbar.addAction(act_select)

        act_add_pair = QAction(QIcon.fromTheme("list-add"), "Add .in/.ans Pair", self)
        act_add_pair.triggered.connect(self.add_pair)
        toolbar.addAction(act_add_pair)

        act_add_folder = QAction(QIcon.fromTheme("folder"), "Add Folder", self)
        act_add_folder.triggered.connect(self.add_folder)
        toolbar.addAction(act_add_folder)

        act_save = QAction(QIcon.fromTheme("document-save"), "Save Report", self)
        act_save.triggered.connect(self.save_report)
        toolbar.addAction(act_save)

        main_layout.addWidget(toolbar)

        top_splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout()

        sol_row = QHBoxLayout()
        self.solution_path = QLineEdit()
        self.solution_path.setReadOnly(True)
        self.solution_path.setPlaceholderText(
            "Drag & drop solution here or use Select Solution"
        )
        self.solution_path.setMinimumHeight(32)
        self.solution_path.setStyleSheet("border-radius:6px; padding:6px;")
        sol_btn = QPushButton("Select")
        sol_btn.clicked.connect(self.select_solution)
        sol_row.addWidget(QLabel("Solution:"))
        sol_row.addWidget(self.solution_path)
        sol_row.addWidget(sol_btn)
        left_layout.addLayout(sol_row)

        btn_row = QHBoxLayout()
        self.compile_btn = QPushButton("Compile / Prepare")
        self.compile_btn.clicked.connect(self.compile_solution)
        self.run_selected_btn = QPushButton("Run Selected")
        self.run_selected_btn.clicked.connect(self.run_selected)
        self.run_all_btn = QPushButton("Run All")
        self.run_all_btn.clicked.connect(self.run_all)
        for b in (self.compile_btn, self.run_selected_btn, self.run_all_btn):
            b.setMinimumHeight(36)
            b.setCursor(Qt.PointingHandCursor)
            self._neonize_button(b)
        btn_row.addWidget(self.compile_btn)
        btn_row.addWidget(self.run_selected_btn)
        btn_row.addWidget(self.run_all_btn)
        left_layout.addLayout(btn_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["#", "Input", "Status", "Time (s)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.show_details_from_table)
        left_layout.addWidget(self.table)

        left_panel.setLayout(left_layout)
        top_splitter.addWidget(left_panel)

        right_splitter = QSplitter(Qt.Vertical)

        log_panel = QWidget()
        log_layout = QVBoxLayout()
        header = QLabel("Live Log")
        header.setStyleSheet("font-weight:600;")
        log_layout.addWidget(header)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumWidth(420)
        log_layout.addWidget(self.log_area)
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        log_layout.addWidget(self.progress)
        log_panel.setLayout(log_layout)
        right_splitter.addWidget(log_panel)

        detail_panel = QWidget()
        detail_layout = QVBoxLayout()
        detail_header = QLabel("Details")
        detail_header.setStyleSheet("font-weight:600;")
        detail_layout.addWidget(detail_header)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        detail_layout.addWidget(self.details)
        detail_panel.setLayout(detail_layout)
        right_splitter.addWidget(detail_panel)

        top_splitter.addWidget(right_splitter)
        top_splitter.setStretchFactor(0, 3)
        top_splitter.setStretchFactor(1, 2)

        main_layout.addWidget(top_splitter)
        central.setLayout(main_layout)
        self.setCentralWidget(central)

        self.setAcceptDrops(True)
        self._setup_shortcuts()
        self._setup_animation_loop()

    def _neonize_button(self, b):
        b.setStyleSheet(
            """
            QPushButton{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #0ea5b7, stop:1 #7c3aed);
                border-radius:8px;
                color: white;
                padding:8px 12px;
                font-weight:600;
            }

            """
        )

    def _setup_shortcuts(self):
        pass

    def _setup_animation_loop(self):
        self._pulse_timer = QTimer()
        self._pulse_timer.timeout.connect(self._animate_compile_button)
        self._pulse_timer.start(2000)

    def _animate_compile_button(self):
        anim = QPropertyAnimation(self.compile_btn, b"geometry")
        rect = self.compile_btn.geometry()
        anim.setDuration(600)
        anim.setStartValue(rect)
        anim.setEndValue(rect.adjusted(-4, -2, 4, 2))
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.setLoopCount(1)
        anim.start()

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        urls = e.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if Path(path).suffix in (".py", ".c", ".cpp"):
            self.solution = path
            self.solution_path.setText(path)
            self.exec_path = None

    def _update_table(self):
        self.table.setRowCount(len(self.testcases))
        for i, (inp, ans) in enumerate(self.testcases):
            idx = QTableWidgetItem(str(i + 1))
            name = QTableWidgetItem(Path(inp).name)
            status_item = QTableWidgetItem("Not Run")
            status_item.setTextAlignment(Qt.AlignCenter)
            time_item = QTableWidgetItem("-")
            time_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, idx)
            self.table.setItem(i, 1, name)
            self.table.setItem(i, 2, status_item)
            self.table.setItem(i, 3, time_item)

    def select_solution(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Solution", "", "Source Files (*.py *.c *.cpp)"
        )
        if not path:
            return
        self.solution = path
        self.solution_path.setText(path)
        self.exec_path = None

    def add_pair(self):
        inp, _ = QFileDialog.getOpenFileName(
            self, "Select Input File", "", "Input Files (*.in);;All Files (*)"
        )
        if not inp:
            return
        ans, _ = QFileDialog.getOpenFileName(
            self, "Select Answer File", "", "Answer Files (*.ans);;All Files (*)"
        )
        if not ans:
            return
        self.testcases.append((inp, ans))
        self._update_table()
        self._log(f"Added pair: {Path(inp).name} ↔ {Path(ans).name}")

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder with .in/.ans pairs"
        )
        if not folder:
            return
        added = 0
        for f in sorted(Path(folder).glob("*.in")):
            ans = f.with_suffix(".ans")
            if ans.exists():
                self.testcases.append((str(f), str(ans)))
                added += 1
        self._update_table()
        self._log(f"Added {added} pairs from folder")

    def compile_solution(self):
        if not self.solution:
            QMessageBox.warning(self, "No solution", "Select a solution first")
            return
        ext = Path(self.solution).suffix
        if ext == ".py":
            self.exec_path = None
            QMessageBox.information(
                self, "Python", "Python script selected — no compilation required"
            )
            return
        exe = tempfile.NamedTemporaryFile(
            delete=False, prefix="judge_exec_", dir=os.getcwd()
        )
        exe.close()
        if ext == ".c":
            cmd = ["gcc", self.solution, "-O2", "-std=c11", "-o", exe.name]
        else:
            cmd = ["g++", self.solution, "-O2", "-std=c++17", "-o", exe.name]
        self._log("Compiling...")
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if proc.returncode != 0:
            QMessageBox.critical(self, "Compilation Error", proc.stderr)
            self._log("Compilation failed")
            return
        self.exec_path = exe.name
        QMessageBox.information(self, "Compiled", f"Compiled → {exe.name}")
        self._log(f"Compiled binary at {exe.name}")

    def prepare_cmd(self):
        if not self.solution:
            return None, "No solution selected"
        ext = Path(self.solution).suffix
        if ext == ".py":
            return [sys.executable, self.solution], None
        if ext in (".c", ".cpp"):
            if not self.exec_path or not Path(self.exec_path).exists():
                self.compile_solution()
            if not self.exec_path:
                return None, "Compilation failed"
            return [self.exec_path], None
        return None, "Unsupported file type"

    def run_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Select", "Select a test row first")
            return
        self.run_indices([row])

    def run_all(self):
        if not self.testcases:
            QMessageBox.warning(self, "No tests", "Add testcases first")
            return
        self.run_indices(list(range(len(self.testcases))))

    def run_indices(self, indices):
        cmd, err = self.prepare_cmd()
        if err:
            QMessageBox.warning(self, "Error", err)
            return
        self.results = [None] * len(self.testcases)
        self.progress.setValue(0)
        total = len(indices)
        completed = 0

        def on_finished(idx, res):
            nonlocal completed
            self.results[idx] = res
            self._update_result_row(idx, res)
            completed += 1
            perc = int((completed / total) * 100)
            self.progress.setValue(perc)
            if completed == total:
                self._log("All executions finished")
                QMessageBox.information(self, "Done", "All testcases executed")

        for i in indices:
            inp, ans = self.testcases[i]
            task = RunTask(i, cmd, inp, ans, timeout=2)
            task.signals.finished.connect(on_finished)
            task.signals.log.connect(self._log)
            self.threadpool.start(task)

    def _update_result_row(self, row, res):
        status_item = QTableWidgetItem(res["status"])
        status_item.setTextAlignment(Qt.AlignCenter)
        if res["status"] == "Accepted":
            status_item.setBackground(QColor("#0f5132"))
        elif res["status"] in ("Wrong Answer",):
            status_item.setBackground(QColor("#4b0000"))
        elif res["status"] in ("TLE",):
            status_item.setBackground(QColor("#4b2b00"))
        elif res["status"] == "RE":
            status_item.setBackground(QColor("#3a1b4b"))
        else:
            status_item.setBackground(QColor("#222222"))
        time_item = QTableWidgetItem(f"{res.get('time', 0):.6f}")
        time_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 2, status_item)
        self.table.setItem(row, 3, time_item)

    def show_details_from_table(self, row, _col):
        if row < 0 or row >= len(self.testcases):
            return
        if not self.results or not self.results[row]:
            QMessageBox.information(self, "Info", "This test has not been run yet.")
            return
        res = self.results[row]
        txt = f"Test #{row + 1}\nStatus: {res['status']}\nTime: {res.get('time', 0):.6f}s\n\n"
        if res.get("stderr"):
            txt += f"--- STDERR ---\n{res['stderr']}\n\n"
        if res.get("stdout"):
            txt += f"--- STDOUT ---\n{res['stdout']}\n\n"
        if res.get("diff"):
            txt += f"--- DIFF ---\n{res['diff']}\n"
        self.details.setPlainText(txt)

    def save_report(self):
        if not self.results or all(r is None for r in self.results):
            QMessageBox.warning(self, "No results", "No results to save")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Report", "", "Text Files (*.txt)"
        )
        if not path:
            return
        with open(path, "w") as f:
            for i, r in enumerate(self.results):
                if not r:
                    f.write(f"Test #{i + 1}\nStatus: Not Run\n\n")
                    continue
                f.write(
                    f"Test #{i + 1}\nStatus: {r['status']}\nTime: {r.get('time', 0):.6f}s\n"
                )
                if r.get("stderr"):
                    f.write(f"--- STDERR ---\n{r['stderr']}\n")
                if r.get("stdout"):
                    f.write(f"--- STDOUT ---\n{r['stdout']}\n")
                if r.get("diff"):
                    f.write(f"--- DIFF ---\n{r['diff']}\n")
                f.write("\n" + "-" * 40 + "\n")
        QMessageBox.information(self, "Saved", f"Report saved to {path}")
        self._log(f"Report saved → {path}")

    def _log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.log_area.append(f"[{ts}] {msg}")

    def _neon_message(self, text):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Neon")
        dlg.setText(text)
        dlg.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    w = App()
    w.show()
    sys.exit(app.exec_())
