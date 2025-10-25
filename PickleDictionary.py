import os
import pickle


class PickleDictionary:
    def __init__(self, filename: str) -> None:
        self._file_path = f"pickles/{filename}"
        self._saved = True

        # Create pickle file if it doesn't exist
        try:
            open(self._file_path, "rb")
        except FileNotFoundError:
            # Ensure parent directory exists before creating the file
            os.makedirs(os.path.dirname(self._file_path) or ".", exist_ok=True)
            with open(self._file_path, "wb") as pickle_file:
                pickle.dump(dict(), pickle_file)

        # Unpickle dictinary
        with open(self._file_path, "rb") as pickle_file:
            self._dictionary = pickle.load(pickle_file)

    def save(self) -> None:
        if not self._saved:
            with open(self._file_path, "wb") as pickle_file:
                pickle.dump(self._dictionary, pickle_file)

            self._saved = True

    def __contains__(self, item) -> bool:
        return item in self._dictionary

    def __getitem__(self, item):
        return self._dictionary[item]

    def __setitem__(self, key, value) -> None:
        self._saved = False
        self._dictionary[key] = value
