import os
from uuid import uuid4
from typing import Optional, Tuple, Union

from getm.http import http


class indirect_open:
    """This should be used as a context manager. Provides a file object to a temporary file. Temporary file is moved to
    'filepath' if no error occurs before close. Attempt to remove temporary file in all cases.
    """
    def __init__(self, filepath: str, tmp: Optional[str]=None):
        self.filepath = filepath
        self.tmp = tmp or f"/tmp/getm-{uuid4()}"

    def __enter__(self):
        self.handle = open(self.tmp, "wb", buffering=0)
        return self.handle

    def __exit__(self, exc_type, exc_value, traceback):
        self.handle.close()
        if exc_type is None:
            if os.path.isfile(self.filepath):
                os.remove(self.filepath)
            os.link(self.tmp, self.filepath)
        os.remove(self.tmp)
