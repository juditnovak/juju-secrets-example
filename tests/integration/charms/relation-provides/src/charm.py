#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Database charm that accepts connections from application charms.

This charm is meant to be used only for testing
of the libraries in this repository.
"""

import logging

from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus

from charms.data_platform_libs.v0.data_interfaces import (
    DatabaseProvides,
    DatabaseRequestedEvent,
)

logger = logging.getLogger(__name__)


class DatabaseCharm(CharmBase):
    """Database charm that accepts connections from application charms."""

    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)

        # Default charm events.
#        self.framework.observe(self.on.database_pebble_ready, self._on_database_pebble_ready)
        self.framework.observe(self.on.start, self._on_start)

        # Charm events defined in the database provides charm library.
        self.provides = DatabaseProvides(self, relation_name="database")
        self.framework.observe(self.provides.on.database_requested, self._on_database_requested)

    def _on_start(self, event) -> None:
        self.unit.status = ActiveStatus()

    def _on_database_requested(self, event: DatabaseRequestedEvent) -> None:
        """Event triggered when a new database is requested."""
        self.unit.status = MaintenanceStatus("creating database")

        # Set the read/write endpoint.
        self.provides.set_endpoints(
            event.relation.id, f'{self.model.get_binding("database").network.bind_address}:5432'
        )

        # Share additional information with the application.
        self.provides.set_tls(event.relation.id, "False")
        self.provides.set_version(event.relation.id, "0.1")

        self.unit.status = ActiveStatus()


if __name__ == "__main__":
    main(DatabaseCharm)
