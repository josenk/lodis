"""
Base implementation of Lodis - Core class structure and helper methods.
"""

import time
from multiprocessing import Lock

from .constants import (
    NUM_DATABASES,
    NO_EXPIRATION,
    TYPE_STRING,
    TYPE_LIST,
    TYPE_SET,
    TYPE_ZSET,
    TYPE_HASH
)


class LodisBase:
    """
    Base class for Lodis - provides core structure and helper methods.

    This class provides the fundamental infrastructure including:
    - Storage management
    - Expiration checking
    - Type checking
    - Thread safety via mutex locks
    """

    def __init__(self, host='localhost', port=6379, db=0, decode_responses=False,
                 socket_timeout=None, socket_connect_timeout=None,
                 socket_keepalive=None, socket_keepalive_options=None,
                 connection_pool=None, unix_socket_path=None,
                 encoding='utf-8', encoding_errors='strict',
                 charset=None, errors=None, retry_on_timeout=False,
                 ssl=False, ssl_keyfile=None, ssl_certfile=None,
                 ssl_cert_reqs='required', ssl_ca_certs=None,
                 ssl_ca_cert_dir=None, ssl_ca_data=None, ssl_check_hostname=False,
                 max_connections=None, single_connection_client=False,
                 health_check_interval=0, client_name=None, username=None,
                 password=None, **kwargs):
        """
        Redis-compatible constructor. Connection parameters are ignored since this is in-memory.
        All data is stored locally without any network connections.

        Args:
            db: Database number (0-15, default 0). Redis supports 16 databases by default.
            decode_responses: Whether to decode responses (stored but not used in this implementation)
            **kwargs: Other Redis connection parameters (ignored)
        """
        # All connection parameters are ignored - this is in-memory storage
        self.decode_responses = decode_responses

        # Validate initial database selection
        if not isinstance(db, int) or db < 0 or db >= NUM_DATABASES:
            raise ValueError(f"invalid DB index: {db} (must be 0-{NUM_DATABASES - 1})")

        # Current database selection
        self._current_db = db

        # Storage: dict of dicts, one per database
        # Structure: {db_num: {key: (expire, data_type, data)}}
        # - expire: timestamp when key expires
        # - data_type: one of TYPE_STRING, TYPE_LIST, TYPE_SET, TYPE_ZSET, TYPE_HASH
        # - data: the actual data (type depends on data_type)
        self._databases = {i: {} for i in range(NUM_DATABASES)}

        self.mutex = Lock()

    @property
    def _keys(self):
        """Get the current database's key storage."""
        return self._databases[self._current_db]

    def _is_expired(self, key):
        """
        Check if key exists and is not expired. Clean up if expired.

        Args:
            key: The key to check

        Returns:
            Tuple of (data_type, data) if key exists and not expired, (None, None) otherwise
        """
        entry = self._keys.get(key, None)
        if entry is None:
            return None, None

        expire, data_type, data = entry

        if expire < time.time():
            with self.mutex:
                if key in self._databases[self._current_db]:
                    del self._databases[self._current_db][key]
            return None, None

        return data_type, data

    def _check_type(self, key, expected_type):
        """
        Check if key exists and has the expected type.
        Raises WRONGTYPE error if key exists but has wrong type.

        Args:
            key: The key to check
            expected_type: Expected data type (TYPE_STRING, TYPE_LIST, etc.)

        Returns:
            True if key doesn't exist or has correct type

        Raises:
            TypeError: If key exists but has wrong type
        """
        data_type, data = self._is_expired(key)
        if data_type is None:
            # Key doesn't exist, which is fine
            return True

        if data_type != expected_type:
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        return True

    def _get_typed_data(self, key, expected_type):
        """
        Get data for key with type checking.

        Args:
            key: The key to retrieve
            expected_type: Expected data type

        Returns:
            Data if key exists and has correct type, None otherwise

        Raises:
            TypeError: If key exists but has wrong type
        """
        data_type, data = self._is_expired(key)
        if data_type is None:
            return None

        if data_type != expected_type:
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        return data
