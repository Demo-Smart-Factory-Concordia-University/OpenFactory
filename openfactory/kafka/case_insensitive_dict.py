""" Provides a case-insensitive dictionary implementation. """

from collections import UserDict


class CaseInsensitiveDict(UserDict):
    """
    Dictionary with case insensitive keys.

    Example:
        >>> d = CaseInsensitiveDict({'Content-Type': 'application/json'})
        >>> d['content-type']
        'application/json'
        >>> d['CONTENT-TYPE']
        'application/json'
    """

    def __getitem__(self, key: str):
        """
        Retrieve the value associated with a key, case-insensitively.

        Args:
            key (str): The key to look up.

        Returns:
            The value corresponding to the key, if found.

        Raises:
            KeyError: If the key is not found in any case.
        """
        key_lower = key.lower()
        for k in self.data.keys():
            if k.lower() == key_lower:
                return self.data[k]
        raise KeyError(key)
