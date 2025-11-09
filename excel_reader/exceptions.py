"""
异常与错误模型
"""
from typing import Optional
from .models import ErrorCode


class SpecError(Exception):
    """规范异常基类"""
    def __init__(self, code: ErrorCode, message: str, hint: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.hint = hint


class InvalidArgumentError(SpecError):
    def __init__(self, message: str = "Invalid argument", hint: Optional[str] = None):
        super().__init__(ErrorCode.INVALID_ARGUMENT, message, hint)


class UnsupportedFormatError(SpecError):
    def __init__(self, message: str = "Unsupported file format", hint: Optional[str] = None):
        super().__init__(ErrorCode.UNSUPPORTED_FORMAT, message, hint)


class FileReadError(SpecError):
    def __init__(self, message: str = "Failed to read file", hint: Optional[str] = None):
        super().__init__(ErrorCode.FILE_READ, message, hint)


class OutputWriteError(SpecError):
    def __init__(self, message: str = "Failed to write outputs", hint: Optional[str] = None):
        super().__init__(ErrorCode.OUTPUT_WRITE, message, hint)

