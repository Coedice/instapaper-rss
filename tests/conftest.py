import os
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture
def temp_pickle_files():
    """Provide a function to generate temp pickle filenames, cleaned up after each test."""
    files = []

    def _get_temp_filename():
        os.makedirs("pickles", exist_ok=True)
        fd, temp_path = tempfile.mkstemp(suffix=".dat", dir="pickles", prefix="test_")
        os.close(fd)
        os.remove(temp_path)
        filename = os.path.basename(temp_path)
        files.append(filename)
        return filename

    yield _get_temp_filename

    for test_file in files:
        file_path = f"pickles/{test_file}"
        if os.path.exists(file_path):
            os.remove(file_path)
