#!/usr/bin/env python3
# Copyright 2023 Shayan
# See LICENSE file for licensing details.

import asyncio
import logging
from pathlib import Path
from typing import Optional

import pytest
import yaml
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./tests/integration/charms/labels-charm/metadata.yaml").read_text())
APP_NAME = METADATA["name"]
UNIT0_NAME = f"{APP_NAME}/0"


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest):
    """Build the charm-under-test and deploy it together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    # Build and deploy charm from local source folder
    charm = await ops_test.build_charm("./tests/integration/charms/labels-charm")
    resources = {
        "secrets-labels-charm-image": METADATA["resources"]["secrets-labels-charm-image"]["upstream-source"]
    }

    # Deploy the charm and wait for active/idle status
    await asyncio.gather(
        ops_test.model.deploy(charm, resources=resources, application_name=APP_NAME, num_units=1),
        ops_test.model.wait_for_idle(
            apps=[APP_NAME], status="active", raise_on_blocked=True, timeout=1000,
            wait_for_exact_units=1
        ),
    )


async def helper_execute_action(
    ops_test: OpsTest, action: str, params: Optional[dict[str, str]] = None
):
    if params:
        action = await ops_test.model.units.get(UNIT0_NAME).run_action(action, **params)
    else:
        action = await ops_test.model.units.get(UNIT0_NAME).run_action(action)
    action = await action.wait()
    return action.results


async def test_add_secret(ops_test: OpsTest):
    """Testing secret update on a joined secret
    """
    # No secrets yet
    secrets_data = await helper_execute_action(ops_test, "get-secret")
    # NOTE: event.set_results() removes keys with empty values
    assert "secret" not in secrets_data

    # Add a secret
    await helper_execute_action(ops_test, "set-secret", {"content": {"key": "value"}})
    secrets_data = await helper_execute_action(ops_test, "get-secret")
    assert secrets_data["secret"]["key"] == "value"

    # Remove all secrets
    await helper_execute_action(ops_test, "forget-default-secret")
    secrets_data = await helper_execute_action(ops_test, "get-secret")
    assert "secret" not in secrets_data


async def test_change_secret(ops_test: OpsTest):
    """Testing secret update on a joined secret
    """
    await helper_execute_action(ops_test, "forget-default-secret")

    content = {f"key{i}": f"value{i}" for i in range(3)}
    await helper_execute_action(ops_test, "set-secret", {'content': content})

    secrets_data = await helper_execute_action(ops_test, "get-secret")

    assert secrets_data["secret"] == {
        "key0": "value0",
        "key1": "value1",
        "key2": "value2",
    }

    for i in range(3):
        await helper_execute_action(ops_test, "set-secret", {"content": {"key0": "newvalue"}})

    secrets_data = await helper_execute_action(ops_test, "get-secret")

    assert secrets_data["secret"]["key0"] == "newvalue"


async def test_delete_secret(ops_test: OpsTest):
    """Testing if it's possible to remove all keys from a joined secret one-by-one in SEPARATE event scopes.
    """
    await helper_execute_action(ops_test, "forget-default-secret")

    content = {f"key{i}": f"value{i}" for i in range(3)}
    await helper_execute_action(ops_test, "set-secret", {"content": content})

    secrets_data = await helper_execute_action(ops_test, "get-secret")

    assert secrets_data["secret"] == {
        "key0": "value0",
        "key1": "value1",
        "key2": "value2",
    }

    for i in range(3):
        await helper_execute_action(ops_test, "delete-secrets", {"keys": [f"key{i}"]})

    secrets_data = await helper_execute_action(ops_test, "get-secret")

    # NOTE: event.set_results() removes keys with empty values
    assert "secret" not in secrets_data
