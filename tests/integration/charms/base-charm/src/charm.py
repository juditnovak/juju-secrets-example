#!/usr/bin/env python3
# Copyright 2023 Shayan
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""A small charm handling secret manipulation within a single Juju Secret object"""

import logging

import ops
from ops import ActiveStatus, SecretNotFoundError
from ops.charm import ActionEvent
from helpers import compare_secret_ids

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

VALID_LOG_LEVELS = ["info", "debug", "warning", "error", "critical"]
PEER = "charm-peer"


class SecretsTestCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)

        self.framework.observe(self.on.start, self._on_start)

        self.framework.observe(self.on.set_secret_action, self._on_set_secret_action)
        self.framework.observe(self.on.get_secrets_action, self._on_get_secrets_action)
        self.framework.observe(self.on.delete_secrets_action, self._on_delete_secrets_action)
        self.framework.observe(self.on.forget_all_secrets_action, self._on_forget_all_secrets_action)
        self.framework.observe(self.on.secret_changed, self._on_secret_changed)

##############################################################################
# Event handlers
##############################################################################

    def _on_start(self, event) -> None:
        self.unit.status = ActiveStatus()

    def _on_set_secret_action(self, event: ActionEvent):
        if self.unit.is_leader():
            content = event.params
            event.set_results({"secret-id": self.set_secret(content)})

    def _on_get_secrets_action(self, event: ActionEvent):
        """Return the secrets stored in juju secrets backend."""
        event.set_results({"secrets": self.get_secrets()})

    def _on_secret_changed(self, event: ActionEvent):
        if not compare_secret_ids(
            event.secret.id, self.app_peer_data["secret-id"]
        ):
            my_secret = self._get_my_secret()
            logging.error({"secrets": {
                "event_secret": event.secret.__dict__,
                "my_secret": my_secret.__dict__
                }
            })

    def _on_delete_secrets_action(self, event: ActionEvent):
        if self.unit.is_leader():
            keys = event.params.get("keys")
            for key in keys:
                self.delete_secret(key)

    def _on_forget_all_secrets_action(self, event: ActionEvent):
        if self.unit.is_leader():
            if self.app_peer_data.get("secret-id"):
                del self.app_peer_data["secret-id"]
                self.secret_meta = None

##############################################################################
# Properties and methods
##############################################################################

    @property
    def peers(self) -> ops.model.Relation:
        """Retrieve the peer relation (`ops.model.Relation`)."""
        return self.model.get_relation(PEER)

    @property
    def app_peer_data(self) -> dict[str, str]:
        """Application peer relation data object."""
        if self.peers is None:
            return {}

        return self.peers.data[self.app]

    def _get_my_secret(self):
        secret_id = self.app_peer_data.get("secret-id")
        if secret_id:
            try:
                return self.model.get_secret(id=secret_id)
            except SecretNotFoundError:
                pass
        return {}

    def get_secrets(self) -> dict[str, str]:
        """Get the secrets stored in juju secrets backend."""
        secret = self._get_my_secret()

        if not secret:
            return {}

        content = secret.get_content()
        logger.info(f"Retrieved secret {self.app_peer_data['secret-id']} with content {content}")
        return content

    def set_secret(self, new_content: dict) -> None:
        """Set the secret in the juju secret storage."""
        secret_id = self.app_peer_data.get("secret-id")

        if secret_id:
            secret = self.model.get_secret(id=secret_id)
            content = secret.get_content()
            content.update(new_content)
            logger.info(f"Setting secret {secret.id} to {content}")
            secret.set_content(content)
        else:
            secret = self.app.add_secret(new_content)
            self.app_peer_data["secret-id"] = secret.id
            logger.info(f"Added secret {secret.id} to {new_content}")

        return secret.id

    def delete_secret(self, key: str) -> None:
        """Remove a secret."""
        secret_id = self.app_peer_data.get("secret-id")

        if not secret_id:
            logging.error("Can't delete any secrets as we have none defined")

        secret = self.model.get_secret(id=secret_id)
        content = secret.get_content()
        if key in content:
            del content[key]
        logger.info(f"Removing {key} from secret {secret.id}")
        logger.info(f"Remaining content is {list(content.keys())}")
        if content:
            secret.set_content(content)
        else:
            secret.remove_all_revisions()
            del self.app_peer_data["secret-id"]


if __name__ == "__main__":  # pragma: nocover
    ops.main(SecretsTestCharm)
