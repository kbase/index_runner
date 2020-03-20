set -a 
# NB we use "valid_admin_token" even when ws_admin is no
WORKSPACE_TOKEN=valid_admin_token
RE_API_TOKEN=valid_admin_token
WS_ADMIN="${WS_ADMIN:=yes}"
SKIP_RELENG="${SKIP_RELENG:=no}"
SKIP_FEATURES="${SKIP_FEATURES:=no}"
READY_TIMEOUT="${READY_TIMEOUT:=60}"
echo "Starting tests with token '${WORKSPACE_TOKEN}' and timeout '${READY_TIMEOUT} second'"
make test
