cd ..
echo "Token is ${TOKEN}"
# This ensures that even if we have local mapping of ci.kbase.us to a local proxy, the
# docker container can still talk to CI.
docker run --rm \
    --net kbase-dev \
    --add-host ci.kbase.us:128.3.56.133 \
    --mount type=bind,source="$(pwd)"/../index_runner_spec,target=/app/config \
    --env SKIP_RELENG=1 \
    --env SKIP_FEATURES=1 \
    --env ELASTICSEARCH_HOST=elasticsearch \
    --env ELASTICSEARCH_PORT=9200 \
    --env KAFKA_SERVER=kafka \
    --env KAFKA_CLIENTGROUP=search_indexer \
    --env KBASE_ENDPOINT=https://ci.kbase.us/services \
    --env WORKSPACE_TOKEN="${TOKEN}" \
    --env WS_ADMIN=no \
    --env MAX_OBJECT_SIZE="${MAX_OBJECT_SIZE}" \
    --env GLOBAL_CONFIG_URL=file://localhost/app/config/confg.yaml \
    --name indexrunner \
    indexrunner:dev
cd local-dev
