# Set TOKEN env var
# Set KBASE_ENV if want next, appdev, or prod
# TODO: support envs other than ci!
cd indexing-scripts
ruby index-own-narratives.rb
ruby index-narratorials.rb
OBJECT_LIMIT=100 ruby index-refseq.rb
OBJECT_LIMIT=50 ruby index-mycocosm.rb
cd ..