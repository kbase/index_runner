require './services'
require './indexing'

# 5947 - an ncbi workspace created by Matt in 2016. Should be deleted.
# $blacklist = [5947, 6306, 6309]

# $refseqWorkspaces = {
#     'ci': 15792,
#     'next': nil,
#     'appdev': nil,
#     'proc': nil
# }

class RefdataIndexer < Indexer
    def filter(workspaceInfo)
        workspaceId = workspaceInfo[0]

        if !isRefdata(workspaceInfo)
            return false
        end

        if !isMetadata(workspaceInfo, 'refdata_source', 'NCBI RefSeq')
            return false
        end

        return true
    end
end

object_limit = ENV['OBJECT_LIMIT']
if object_limit != nil
    object_limit = object_limit.to_i
end
puts "ObjectLimit: #{object_limit}"

indexer = RefdataIndexer.new
indexer.index_workspace_objects object_limit: object_limit