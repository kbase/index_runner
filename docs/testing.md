# Testing

The simplest invocation of tests is to simply do:

```bash
make test
```

at the top level of the repo. All you need is `make` and `docker`.

This uses `docker-compose` to pull, build, and launch the search indexer and all dependent services. Since those services include elasticsearch, kafka, arrango, relation engine, the host requirements are pretty high. I run this on macOS docker with 6G memory, 100G drive, 4 core, and the 2017 machine whirs and heats up, but handles the load ok.

Since tests are run using mocks, a real KBase token is not required, but the fake one must be specified.

## Environment Variables

The docker compose file propagates or sets several environment variables. Presented below are the ones you probably want to fiddle with.

All environment variables which can be set for testing are preset in the `.env` file located in the root of the repo. Variables set in the shell will override those in `.env`, so it really serves as a set of defaults.

### required

- `WORKSPACE_TOKEN` - for tests this should always be `valid_admin_token`
- `RE_API_TOKEN` - for tests this should always be `valid_admin_token`

### optional (with defaults)

- `WS_ADMIN` - whether to run the admin workspace calls or not; note that the token ordinarily should match the admin capabilities configured, but all tests use the fake token `valid_admin_token`; defaults to `yes`
- `SKIP_RELENG` - whether to skip relation engine code paths and tests; defaults to `no`
- `READY_TIMEOUT` - how long to wait for the index runner service to be ready before giving up; the index runner polls ES and RE for readiness, which can take a while; defaults to `60` seconds.

## Easy script

Another technique is to use:

```bash
bash scripts/local-test.sh
```

This script provides default values for the same environment variables as .env does.
