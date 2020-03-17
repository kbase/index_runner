cd ..
export ELASTICSEARCH_HOST=kbase-dev
export ELASTICSEARCH_PORT=9200
export KBASE_ENDPOINT=https://ci.kbase.us
# set the following from the command line!
# export WORKSPACE_TOKEN=XXX -
docker-compose up 
cd local-dev