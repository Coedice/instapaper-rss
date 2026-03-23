import os

from PickleDictionary import PickleDictionary


def test_creates_file_and_directory(temp_pickle_files):
    filename = temp_pickle_files()
    p = PickleDictionary(filename)
    assert os.path.exists(f"pickles/{filename}")
    # Empty dict initially
    try:
        _ = p["missing"]
        assert False, "Expected KeyError for missing key"
    except KeyError:
        pass


def test_setitem_and_save_persistence(temp_pickle_files):
    filename = temp_pickle_files()
    p = PickleDictionary(filename)
    p["a"] = 1
    p.save()

    # Reload and ensure value is persisted
    p2 = PickleDictionary(filename)
    assert p2["a"] == 1


def test_contains_and_getitem(temp_pickle_files):
    filename = temp_pickle_files()
    p = PickleDictionary(filename)
    p["x"] = "y"
    assert "x" in p
    assert p["x"] == "y"
