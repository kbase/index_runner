# Local Development Tools and Docs

This document describes a workflow that has been useful for at least one developer.

## Setup

### get elastic search

Although this repo includes a docker-compose configuration with an included elasticsearch container, we use a separate ES instance.

This is useful because it allows usage of ES for searchapi2 development even when the indexer is not running. We also want to control the location of the ES index files (`local-dev/esdata`) so we can ensure it is persistent between container launches.

see

[https://www.elastic.co/guide/en/elasticsearch/reference/7.5/docker.html](https://www.elastic.co/guide/en/elasticsearch/reference/7.5/docker.html)

or

```text
docker pull elasticsearch:7.5.0
```

### set up docker network

create a local private docker network for things to talk across

```text
docker network create kbase-dev
```

> This is the same network used by kbase-ui, which provides proxying to local services; if you are working with kbase-ui this network is probably already created.

### Start elasticsearch

```text
docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" --net kbase-dev -v `pwd`/esdata:/usr/share/elasticsearch/data elasticsearch:7.5.0
```

Once it is started the first time, you can use Docker Desktop to stop and start it.

### Start kafka

Kafka needs to be started up before the indexer is started. The indexer ensures that required services (Kafka, Elasticsearch) are operating before it starts.

```text
cd local-dev/kafka
docker-compose up
```

#### Resetting Kafka

If you are recovering from an indexing snafu, which has generated many kafka events for indexing, you will probably want to shut down Kafka and remove all pending events. This is described in a latter section.

```text
docker-compose down -v --remove-orphans
```

## Start the indexer

The canonical easy start for the indexer

```bash
TOKEN=ABC123 bash run.sh
```

This will start the indexer, using the indicated token for all interactions with KBase services, and use the non-admin workspace api.

[ this section still being written ]
setup for the indexer is via env variables. there are many, but the required ones for us are:

- `SKIP_RELENG=1`
- `ALLOW_INDICES=narrative`
- `ELASTICSEARCH_HOST=elasticsearch`
- `ELASTICSEARCH_PORT=9200`
- `KAFKA_SERVER=kafka`
- `KAFKA_CLIENTGROUP=search_indexer`
- `KBASE_ENDPOINT=https://ci.kbase.us/services`
- ``GLOBAL_CONFIG_URL=file:$(cd `pwd`/../index_runner_spec && pwd)``
- `WORKSPACE_TOKEN=`YOUR CI LOGIN TOKEN
- `WS_ADMIN=` `yes` or `no` (or 1 or 0, or true or false, or t or f, or any combination thereof)
- `WS_USER=`USERNAME ASSOCIATED WITH WS TOKEN IF `WS_ADMIN` is 0

Don't worry -- the `run.sh` script takes care of most of the hardcoded environment variables.

### Required variables

#### `TOKEN`

a KBase auth token (e.g. login token).

By default this is assumed to be a regular user token, with any special admin privs.

### Optional variables

#### `WS_ADMIN`

boolean string value (yes, no, y, n, true, false, t, f, 1, 0) defaults to `no`. 

Whether or not the `TOKEN` carries workspace admin privileges. For local development, this should probably be left alone, which defaults to `no`. Admin privs are useful for indexing private workspaces for multiple other users.

> For local dev and testing, if you are contemplating whether you need an admin token, consider that you can index multiple users by using candidate test accounts as well. E.g. `kbasesearchtest1`, `kbasesearchtest2`, and `kbasesearchtest3` exist in CI for this purpose. A bit tedious to set up, but once done you can safely index in any environment without endangering global workspace security.

#### `SKIP_RELENG`

boolean string value (yes, no, y, n, true, false, t, f, 1, 0) defaults to `yes`.

If true, will cause the search indexer to not process indexing events into the relation engine. When iterating on search indexing, relation engine indexing is probably out of scope.

Also note that instructions in this doc presume that relation engine indexing is disabled.

#### `SKIP_FEATURES`

boolean string value (yes, no, y, n, true, false, t, f, 1, 0) defaults to `yes`.

If true, the default, Genome features will not be indexed. Indexing genomes can dramatically increase the time it takes to index workspaces containing Genomes. Unless you are testing genome feature indexing, it is best to disable this feature.

#### `MAX_OBJECT_SIZE`

an integer string value, defaults to "100000000" (100 million)

Only objects at or below this value will be indexed. This is handy for local development which is usually operating in a resource constrained environment (your laptop!). Disabling this (by setting it to an empty string) is not advisable, as a large object can crash the indexer. This can interrupt and otherwise easy indexing process.

#### `HOST`

a hostname, defaults to `ci.kbase.us`

The host for forming urls to KBase services may be specified, and defaults to the CI host.

Note that the `HOST_IP` needs to be specified if the `HOST` is.

#### `HOST_IP`

an ip address, defaults to `128.3.56.133`.

When you are using a local proxy to kbase, the indexer running inside the docker container will consult your host for hostname lookup. E.g. if you are proxying `ci.kbase.us` in order to route such calls locally, a docker container which needs to contact the "real" ci.kbase.us will instead talk to the proxy. Ordinarily this would be fine -- the proxy would route the request to the real ci.kbase.us. But in local development with the kbase-ui proxy, the dev ssl cert will not be recognized by the indexer, and will throw an error.

Future work make allow us to overcome this, e.g. by installing the local dev cert for *.kbase.us in the indexer container.

In any case, the `HOST_IP` setting, in combination with the `HOST`, is used to set up a special DNS route for the container, via the `-add-host` option.

## Indexing Test Data

Local indexing is conducted against an active KBase deployment which supports at least the following services:

- workspace
- auth
- user profile

and in addition, indexers may rely upon other core or dynamic services.

The `local-dev` directory contains a number of scripts with which you can index entire classes of workspaces. The scope of these scripts is at the workspace level, so all objects within a workspace will be indexed.

Well, that is a lie. There are object-level filters for:

- object size (`MAX_OBJECT_SIZE`)
- blacklisted types (defined the indexer spec)

The scripts are easy enough to understand that if you have a special case, it should be feasible to create a custom indexing script. If it is generally useful, check it in!

### Using the scripts

The scripts are, at present, implemented in Ruby. All you need is a relatively recent version of Ruby 2.X. No external dependencies are required.

For example, to index all of the narratorials:

```bash
cd local-dev/indexing-scripts
TOKEN=ABC123 ruby index-narratorials.rb
```

The indexing scripts:

- `index-own-narratives.rb` - indexes all narratives owned by or shared with the user associated with the given token. Note that this may include narratives indexed by other scripts (narratorial, public), but redundant indexings are okay.
- `index-narratorials.rb` - indexes all public narratives marked as `narratorials` in the workspace metadata.
- `index-public-narratives.rb` - indexes all public narratives
- `index-refseq.rb` - indexes all objects in the refseq workspace; each deploy environment's workspace should have 1 workspace containing refseq reference genomes. The script file defines a map of environment to workspace id.

#### Env variables

#### `TOKEN`

A KBase token. Required.

The token should be the same one (or associated with the same user) as used for the indexer.

#### `KBASE_ENV`

The KBase deployment environment, either `ci`, `next`, `appdev`, or `prod`. Optional, defaults to `ci`.

> TODO: convert scripts to python.

## Index workspaces

Now that that's settled, here is the procedure for indexing workspaces for local dev and testing.

### Index narratives for `kbasesearchtest1` user

Indexing private workspaces for the `kbasesearchtest1` user is useful for supporting tests because the set of found objects will only vary as the narratives owned or shared with this user are changed.

> TODO: Should create another one or two test users in order to be able to test specific sharing scenarios.

```bash
TOKEN=MYTOKEN ruby index-own-narratives.rb
```

Where `MYTOKEN` is a login token for kbasesearchtest1.

### Index 1000 refseq genomes

In order to exercise the indexer, and provide a good coverage of genome types, you can index a subset of refseq genomes. By default features are not indexed. Since features greatly increase the index time, a lower limit is recommended if features are to be indexed.

```bash
TOKEN=MYTOKEN LIMIT=1000 ruby index-refseq.rb
```

> Note that refseq indexing relies on the refseq workspace being properly configured: the `searchtags` metadata field with a value of `"refdata"`, and a `refdata_source` field with a value of `"NCBI RefData"`.


### Index 1000 MycoCosm genomes

MycoCosm genoms are larger, so it is recommended to limit the load to 100 genomes.

```bash
TOKEN=MYTOKEN LIMIT=100 ruby index-mycocosm.rb
```

> Note that the mycocosm workspace, in CI at least, is not configured properly, so the indexer script simply uses the workspace id.

### Index narratorials

Narratorials are our most prominent public Narratives, so their including them in test indexes ensures they index well.

```bash
TOKEN=MYTOKEN ruby index-narratorials.rb
```

> Note that narratorials are identified by a workspace metadata field `narratorial` with a value of 1 (or any other boolean-ish value)

### Index public narratives

Public workspaces offer a good semi-randomized assortment of Narratives with different types of data objects. In order to keep the indexing time tractable, we limit it to the first 1000 Narratives.

```bash
TOKEN=MYTOKEN LIMIT=100 ruby index-public-narratives.rb
```

### Index refseq

```bash
TOKEN=MYTOKEN LIMIT=100 ruby index-refseq.rb
```


### Index mycocosm

```bash
TOKEN=MYTOKEN LIMIT=100 ruby index-mycocosm.rb
```

## Troubleshooting

### ES Limits

The default configuration for ES does not provide enough room for the database to grow. A couple of runtime configuration changes are required to stably index enough workspaces. For perspective, I've used this to index a handful of private workspaces, 3000 refseq genomes, all (2) narratorials, and all public workspaces in CI.

#### Remove replicas

We don't need replicas for a local dev setup, so we remove replicas, which by default are 1 (which doubles the number of shards per index.)

```text
PUT /*/_settings
```

```json
{
    "index" : {
        "number_of_replicas":0,
        "auto_expand_replicas": false
    }
}
```

#### Increase the shards per node

In addition, the number of shards per node defaults to 1000, which runs out pretty quickly While more shards per node is not recommended for production, it seems to work fine to bump up the value to 5000 for local usage.

This worked for a while, then needed another

```text
PUT http://localhost:9200/_cluster/settings
```

```json
{
    "transient": {
        "cluster.max_shards_per_node": 5000
    }
}
```


## Future Work

- TODO: perhaps replace WS_ADMIN/WS_USER with DEV_USERNAME which would both set WS_ADMIN to false (by default true), and set the username associated with the token.

- install dev ssl cert into indexer container

- use call to ws to determine if token is for admin, rather than pass a flag. Shane asked me to hold off on this.

- convert indexing scripts to python