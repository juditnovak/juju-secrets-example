#!/usr/bin/env python3
# Copyright 2023 Shayan
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""A small charm handling secret manipulation within a single Juju Secret object"""

import logging
from typing import Optional, Dict

import ops
from ops import ActiveStatus, SecretNotFoundError, SecretInfo, Secret
from ops.charm import ActionEvent, CharmBase

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

VALID_LOG_LEVELS = ["info", "debug", "warning", "error", "critical"]
PEER = "charm-peer"

SECRET_DEFAULT_LABEL = "mysecret"


class CachedSecret:
    """Internal helper class locally cache secrets.

    The data structure is precisely re-using/simulating as in the actual Secret Storage
    """

    def __init__(self, charm: CharmBase, label: str) -> None:
        self._secret_meta = None
        self._secret_content = {}
        self._secret_label = label
        self.charm = charm

    def add_secret(self, content: Dict[str, str]) -> Secret:
        """Create a new secret."""
        secret = self.charm.app.add_secret(content, label=self._secret_label)
        self._secret_meta = secret
        return self._secret_meta

    @property
    def meta(self) -> Optional[Secret]:
        """Getting cached secret meta-information."""
        if not self._secret_meta:
            try:
                self._secret_meta = self.charm.model.get_secret(label=self._secret_label)
            except SecretNotFoundError:
                return
        return self._secret_meta

    def get_content(self) -> Dict[str, str]:
        """Getting cached secret content."""
        if not self._secret_content:
            if self.meta:
                self._secret_content = self.meta.get_content()
        return self._secret_content

    def set_content(self, content: Dict[str, str]) -> None:
        """Setting cached secret content."""
        if self.meta:
            self.meta.set_content(content)
            self._secret_content = content

    def get_info(self) -> Optional[SecretInfo]:
        """Wrapper function to provide direct access to contained Secret's equal function."""
        if self.meta:
            return self.meta.get_info()


class SecretCache:
    def __init__(self, charm):
        self.charm = charm
        self._secrets = {}

    def get(self, label):
        if not self._secrets.get(label):
            secret = CachedSecret(self.charm, label)
            if secret.meta:
                self._secrets[label] = secret
        return self._secrets.get(label)

    def add(self, label, content):
        if not self._secrets.get(label):
            secret = CachedSecret(self.charm, label)
            secret.add_secret(content)
            self._secrets[label] = secret
        return self._secrets.get(label)


class SecretsTestCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)

        self.framework.observe(self.on.start, self._on_start)

        self.framework.observe(self.on.set_secret_action, self._on_set_secret_action)
        self.framework.observe(self.on.get_secret_action, self._on_get_secret_action)
        self.framework.observe(self.on.delete_secrets_action, self._on_delete_secrets_action)
        self.framework.observe(self.on.forget_default_secret_action, self._on_forget_default_secret_action)

        self.secret_cache = SecretCache(self)

##############################################################################
# Event handlers
##############################################################################

    def _on_start(self, event) -> None:
        self.unit.status = ActiveStatus()

    def _on_set_secret_action(self, event: ActionEvent):
        if self.unit.is_leader():
            label = event.params.get("label")
            content = event.params.get("content")
            if label:
                event.set_results({self.generate_label(label): self.set_secret(content, label)})
            else:
                event.set_results({self.generate_label(): self.set_secret(content)})

    def _on_get_secret_action(self, event: ActionEvent):
        """Return the secrets stored in juju secrets backend."""
        label = event.params.get("label")
        if label:
            event.set_results({"secret": self.get_secret()})
        else:
            event.set_results({"secret": self.get_secret()})

    def _on_delete_secrets_action(self, event: ActionEvent):
        if self.unit.is_leader():
            label = event.params.get("label")
            keys = event.params.get("keys")
            for key in keys:
                if label:
                    self.delete_secret(key, label)
                else:
                    self.delete_secret(key)

    def _on_forget_default_secret_action(self, event: ActionEvent):
        if self.unit.is_leader():
            label = event.params.get("label")
            if label:
                self.delete_full_secret(label)
            else:
                self.delete_full_secret()

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

    def generate_label(self, label: Optional[str] = SECRET_DEFAULT_LABEL):
        """Generate label on the fly"""
        return f"{self.app.name}.{label}"

    def _get_my_secret(self, label: Optional[str] = SECRET_DEFAULT_LABEL):
        full_label = self.generate_label(label)
        try:
            return self.secret_cache.get(label=full_label)
        except SecretNotFoundError:
            pass
        return {}

    def get_secret(self, label: Optional[str] = SECRET_DEFAULT_LABEL) -> dict[str, str]:
        """Get the secrets stored in juju secrets backend."""
        secret = self._get_my_secret(label)

        if not secret:
            return {}

        content = secret.get_content()
        logger.info(f"Retrieved secret {self.generate_label(label)} with content {content}")
        return content

    def set_secret(self, new_content: dict, label: Optional[str] = SECRET_DEFAULT_LABEL) -> None:
        """Set the secret in the juju secret storage."""
        full_label = self.generate_label(label)
        secret = self._get_my_secret(label=label)

        if secret:
            content = secret.get_content()
            content.update(new_content)
            logger.info(f"Setting secret {full_label} to {content}")
            secret.set_content(content)
        else:
            secret = self.secret_cache.add(label=full_label, content=new_content)
            logger.info(f"Added secret {full_label} with {new_content}")

        return secret.meta.id

    def delete_secret(self, key: str, label: Optional[str] = SECRET_DEFAULT_LABEL) -> None:
        """Remove a secret."""
        secret = self._get_my_secret(label=label)

        if not secret:
            logging.error("Can't delete any secrets as we have none defined")

        content = secret.get_content()
        if key in content:
            del content[key]
        logger.info(f"Removing {key} from secret {secret.meta.id}")
        logger.info(f"Remaining content is {list(content.keys())}")
        if content:
            secret.set_content(content)
        else:
            secret.meta.remove_all_revisions()

    def delete_full_secret(self, label: Optional[str] = SECRET_DEFAULT_LABEL) -> None:
        """Remove the complete secret"""
        full_label = self.generate_label(label)
        try:
            secret = self.secret_cache.get(label=full_label)
        except SecretNotFoundError:
            return

        if secret:
            secret.meta.remove_all_revisions()


if __name__ == "__main__":  # pragma: nocover
    ops.main(SecretsTestCharm)
