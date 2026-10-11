"""
Universal NAND Flash Clone Tool - Background Operation Worker
Runs long-running Dump, Write, Erase, and Scan operations asynchronously in a QThread.
"""

import traceback
from typing import Dict, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal

from ...core.nand_engine import NANDEngine, ProgressUpdate


class OperationWorker(QThread):
    progress_updated = pyqtSignal(object) # ProgressUpdate
    operation_finished = pyqtSignal(dict)
    operation_failed = pyqtSignal(str)
    log_emitted = pyqtSignal(str, str) # level, message

    def __init__(
        self,
        engine: NANDEngine,
        task_name: str,
        params: Dict[str, Any],
        parent=None
    ):
        super().__init__(parent)
        self.engine = engine
        self.task_name = task_name
        self.params = params

    def run(self):
        try:
            self.log_emitted.emit("INFO", f"Starting operation: {self.task_name}")

            if self.task_name == "DUMP":
                filepath = self.params.get("filepath", "dump.bin")
                include_oob = self.params.get("include_oob", True)
                start_block = self.params.get("start_block", 0)
                end_block = self.params.get("end_block", None)

                res = self.engine.dump_flash(
                    output_filepath=filepath,
                    include_oob=include_oob,
                    start_block=start_block,
                    end_block=end_block,
                    progress_cb=self._on_progress
                )
                self.operation_finished.emit(res)

            elif self.task_name == "WRITE":
                filepath = self.params.get("filepath")
                skip_bad = self.params.get("skip_bad", True)
                erase_before = self.params.get("erase_before", True)
                start_block = self.params.get("start_block", 0)

                res = self.engine.write_flash(
                    input_filepath=filepath,
                    skip_bad_blocks=skip_bad,
                    erase_before_write=erase_before,
                    start_block=start_block,
                    progress_cb=self._on_progress
                )
                self.operation_finished.emit(res)

            elif self.task_name == "ERASE":
                start_block = self.params.get("start_block", 0)
                end_block = self.params.get("end_block", None)

                ok = self.engine.erase_chip(
                    start_block=start_block,
                    end_block=end_block,
                    progress_cb=self._on_progress
                )
                self.operation_finished.emit({"success": ok})

            elif self.task_name == "SCAN_BAD_BLOCKS":
                bad_blocks = self.engine.scan_bad_blocks(progress_cb=self._on_progress)
                self.operation_finished.emit({"bad_blocks": bad_blocks, "count": len(bad_blocks)})

            else:
                raise ValueError(f"Unknown task: {self.task_name}")

        except Exception as e:
            err_trace = traceback.format_exc()
            self.log_emitted.emit("ERROR", f"Operation failed: {e}\n{err_trace}")
            self.operation_failed.emit(str(e))

    def _on_progress(self, update: ProgressUpdate):
        self.progress_updated.emit(update)

    def request_abort(self):
        self.engine.abort()

