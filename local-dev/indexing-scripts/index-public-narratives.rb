require './services'
require './indexing'

class PublicNarrativeIndexer < Indexer
    def filter(workspaceInfo)

        if !isNarrative(workspaceInfo) 
            return false
        end

        if isRefdata(workspaceInfo)
            return false
        end

        if !isPublic(workspaceInfo)
            return false
        end

        if isNarratorial(workspaceInfo)
            return false
        end

        return true
    end
end

indexer = PublicNarrativeIndexer.new
indexer.index