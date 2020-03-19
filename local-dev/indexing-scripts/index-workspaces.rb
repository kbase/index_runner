require './services'
require './indexing'

# 5947 - an ncbi workspace created by Matt in 2016. Should be deleted.
# $blacklist = [5947, 6306, 6309]

$refseqWorkspaces = {
    'ci': 15792,
    'next': nil,
    'appdev': nil,
    'proc': nil
}

class WorkspacesIndexer < Indexer
    def initialize(token: nil, blacklist: [], limit: nil, workspaces: ) {
        super(token: token, blacklist: blacklist, limit: limit)
        @workspaces = workspaces
    }
    def filter(workspaceInfo)
        workspaceId = workspaceInfo[0]

        if !@workspaces.include? workspaceId
            return false
        end

        return true
    end
end

workspaces = ENV['WORKSPACES']
if workspaces == nil
    raise 'Error: WORKSPACES env variable is required'
}
workspaces = workspaces.split(',').map do |idString| 
    idString.to_i
end
p "Workspaces: #{workspaces}"

indexer = WorkspacesIndexer.new(workspaces: workspaces)
indexer.index