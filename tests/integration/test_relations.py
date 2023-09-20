#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
import asyncio
import logging
from pathlib import Path

import pytest
import yaml
from pytest_operator.plugin import OpsTest

# from .helpers import build_connection_string, get_application_relation_data

logger = logging.getLogger(__name__)

REQUIRES = "relation-requires"
PROVIDES = "relation-provides"
PROVIDES_METADATA = yaml.safe_load(
    Path("./tests/integration/charms/relation-provides/metadata.yaml").read_text()
)
DATABASE_RELATION_NAME = "database"


@pytest.mark.abort_on_fail
async def test_deploy_charms(ops_test: OpsTest):
    """Deploy both charms (application and database) to use in the tests."""
    # Deploy both charms (2 units for each application to test that later they correctly
    # set data in the relation application databag using only the leader unit).

    charm_path = "./tests/integration/charms/relation-provides"
    database_charm = await ops_test.build_charm(charm_path)

    charm_path = "./tests/integration/charms/relation-requires"
    application_charm = await ops_test.build_charm(charm_path)

    await asyncio.gather(
        ops_test.model.deploy(
            application_charm, application_name=REQUIRES, num_units=1, series="jammy"
        ),
        ops_test.model.deploy(
            database_charm,
            application_name=PROVIDES,
            num_units=1,
            series="jammy",
        ),
    )
    await ops_test.model.wait_for_idle(
        apps=[REQUIRES, PROVIDES], status="active", wait_for_exact_units=1
    )


@pytest.mark.abort_on_fail
async def test_database_relation_with_charm_libraries(ops_test: OpsTest):
    """Test basic functionality of database relation interface."""
    # Relate the charms and wait for them exchanging some connection data.
    await ops_test.model.add_relation(
        f"{REQUIRES}:{DATABASE_RELATION_NAME}", PROVIDES
    )
    await ops_test.model.wait_for_idle(apps=[REQUIRES, PROVIDES], status="active")

    unit_provides_name = f"{PROVIDES}/0"
    raw_data = (await ops_test.juju("show-unit", unit_provides_name))[1]
    data_provides = yaml.safe_load(raw_data)

    assert 'tls' in data_provides[unit_provides_name]['relation-info'][0]['application-data']['requested-secrets']

    unit_requires_name = f"{REQUIRES}/0"
    raw_data = (await ops_test.juju("show-unit", unit_requires_name))[1]
    data_requires = yaml.safe_load(raw_data)

    assert 'secret-tls' in data_requires[unit_requires_name]['relation-info'][0]['application-data']
