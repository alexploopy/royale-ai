import subprocess
import sys
import time
import numpy as np
import cv2
from typing import Optional

class ADBClient:
    def __init__(self, serial: str, adb: str = "adb"):
        self.serial = serial
        self.adb = adb
        self.proc: Optional[subprocess.Popen] = None

    def open(self) -> None:
        if self.proc and self.proc.poll() is None:
            return

        creationflags = 0
        startupinfo = None
        if sys.platform.startswith("win"):
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        self.proc = subprocess.Popen(
            [self.adb, "-s", self.serial, "shell"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            creationflags=creationflags,
            startupinfo=startupinfo,
        )
        self.connect()

    def _write(self, cmd: str) -> None:
        if not self.proc or self.proc.poll() is not None:
            raise RuntimeError("ADB shell is not open or has exited.")
        try:
            assert self.proc.stdin is not None
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()
        except BrokenPipeError as e:
            raise RuntimeError("ADB shell pipe is broken (device disconnected?)") from e

    def connect(self) -> None:
        subprocess.run([self.adb, "connect", self.serial], 
                       stdout=subprocess.DEVNULL, 
                       stderr=subprocess.DEVNULL, 
                       check=False)

    def tap(self, x: int, y: int) -> None:
        if x < 0 or y < 0:
            raise ValueError("x and y must be >= 0")
        self._write(f"input tap {int(x)} {int(y)}")
        
        # Delay to ensure commands are processed
        time.sleep(0.1)

    def screen_capture(self) -> np.ndarray:
        """
        Capture a full-resolution frame via RAW adb screencap.
        Returns an OpenCV BGR image (H x W x 3).
        """
        proc = subprocess.run(
            [self.adb, "-s", self.serial, "exec-out", "screencap"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout:
            raise RuntimeError("raw screencap failed")

        data = proc.stdout
        if len(data) < 12:
            raise RuntimeError("raw header too short")

        w  = int.from_bytes(data[0:4],  "little")
        h  = int.from_bytes(data[4:8],  "little")

        payload = memoryview(data)[12:]
        expected = w * h * 4
        if len(payload) < expected:
            raise RuntimeError("raw payload truncated")

        arr_rgba = np.frombuffer(payload[:expected], dtype=np.uint8).reshape(h, w, 4)
        frame_bgr = cv2.cvtColor(arr_rgba, cv2.COLOR_RGBA2BGR)
        
        time.sleep(0.1)
        return frame_bgr
    
    def close(self) -> None:
        # Delay to ensure commands are processed
        time.sleep(0.25)
        
        if not self.proc:
            return
        try:
            if self.proc.stdin:
                self.proc.stdin.write("exit\n")
                self.proc.stdin.flush()
                self.proc.stdin.close()
        finally:
            self.proc.terminate()
            self.proc = None

    def __enter__(self):
        self.open()
        return self
    def __exit__(self, exc_type, exc, tb):
        self.close()
