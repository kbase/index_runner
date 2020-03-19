require './services'
require './indexing'

# 5947 - an ncbi workspace created by Matt in 2016. Should be deleted.
# $blacklist = [5947, 6306, 6309]

$mycocosmWorkspaces = {
    'ci': 32690,
    'next': nil,
    'appdev': nil,
    'proc': nil
}


class MycocosmIndexer < Indexer
    def filter(workspaceInfo)
        workspaceId = workspaceInfo[0]

        if workspaceId == $mycocosmWorkspaces[:ci]
            return true
        end

        if !isRefdata(workspaceInfo)
            return false
        end

        if !isMetadata(workspaceInfo, 'refdata_source', 'MycoCosm')
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

indexer = MycocosmIndexer.new
indexer.index_workspace_objects object_limit: object_limit