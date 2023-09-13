<!--
Avoid using this README file for information that is maintained or published elsewhere, e.g.:

* metadata.yaml > published on Charmhub
* documentation > published on (or linked to from) Charmhub
* detailed contribution guide > documentation or CONTRIBUTING.md

Use links instead.
-->

# juju-secrets-example


Demonstration of Juju Secrets usage in Charms.


## Description

Juju Secrets usage in charms is demonstrated via [Integration Tests](tests/integration/charms/), equipped with pipelines executing code that triggers basic functionality.

The code may server well as an example, or to be taken "as it is" and used when embedding Juju Secrets usage to actual Charms.

### Use cases 

 - [Base charm](tests/integration/charms/base-charm/)
   - Basic Juju Secrets usage. Single secret across the charm, with the URI saved in the peer databag.
   - Real life use-case: MySQL, Postgres
 - [Charm using labels](tests/integration/charms/labels-charm/)
   - Similar use-case as above, except using labels within the charm. Thus no databag usage is needed, labels are automatically generated
   - Real-life use case: Opensearch
 - [Caching secrets for even scope](tests/integration/charms/cache-charm/)
   - Avoding access to Juju Secrets store on each reference to secrets contents
   - In all our charms we're using this technique
 - [Charm Relation secrets Provider](tests/integration/charms/relation-provides/), [Charm Relation secrets Requirer](tests/integration/charms/relation-requires/)
   - Both sides of a Charm Relation
   - NOTE: `data_platform_libs/data_interaces` module outdated
