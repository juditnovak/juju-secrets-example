#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Database charm that accepts connections from application charms.

This charm is meant to be used only for testing
of the libraries in this repository.
"""

import logging
import secrets
import string

from ops.charm import CharmBase, ActionEvent
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
        self.framework.observe(self.on.set_password_action, self._on_set_password_action)

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
        password = self._new_password()
        self.provides.set_credentials(event.relation.id, "admin", password)
        self.provides.set_tls(event.relation.id, "False")
        self.provides.set_version(event.relation.id, "0.1")

        self.unit.status = ActiveStatus()

    def _on_set_password_action(self, event: ActionEvent):
        """Change the admin password."""
        password = self._new_password()
        for relation in self.provides.relations:
            self.provides.update_relation_data(relation.id, {"password": password})

    def _new_password(self) -> str:
        """Generate a random password string."""
        choices = string.ascii_letters + string.digits
        return "".join([secrets.choice(choices) for i in range(16)])


if __name__ == "__main__":
    main(DatabaseCharm)
