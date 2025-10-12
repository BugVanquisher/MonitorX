# Copyright 2025 MonitorX Team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Optional
from contextvars import ContextVar

from .client import MonitorXClient


class MonitorXContext:
    """Context manager for MonitorX client across decorators."""

    _client: ContextVar[Optional[MonitorXClient]] = ContextVar('monitorx_client', default=None)

    @classmethod
    def set_client(cls, client: MonitorXClient) -> None:
        """Set the MonitorX client in the current context."""
        cls._client.set(client)

    @classmethod
    def get_client(cls) -> Optional[MonitorXClient]:
        """Get the MonitorX client from the current context."""
        return cls._client.get()

    @classmethod
    def clear_client(cls) -> None:
        """Clear the MonitorX client from the current context."""
        cls._client.set(None)

    def __init__(self, client: MonitorXClient):
        self.client = client
        self._token = None

    def __enter__(self):
        """Enter the context and set the client."""
        self._token = self._client.set(self.client)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and clear the client."""
        if self._token is not None:
            self._client.reset(self._token)