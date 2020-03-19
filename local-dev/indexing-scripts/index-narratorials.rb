require './services'
require './indexing'

class NarratorialIndexer < Indexer
    def filter(workspaceInfo)
        isNarratorial(workspaceInfo)
    end
end

indexer = NarratorialIndexer.new
indexer.index
