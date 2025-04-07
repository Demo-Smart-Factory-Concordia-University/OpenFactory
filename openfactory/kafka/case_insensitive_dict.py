from collections import UserDict


class CaseInsensitiveDict(UserDict):
    """
    Dictionary with case insensitive keys
    """

    def __getitem__(self, key):
        key_lower = key.lower()
        for k in self.data.keys():
            if k.lower() == key_lower:
                return self.data[k]
        raise KeyError(key)
