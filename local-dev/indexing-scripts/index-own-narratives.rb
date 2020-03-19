require './services'
require './indexing'

class OwnNarrativeIndexer < Indexer
    def initialize(token: nil, blacklist: [], limit: nil)
        super(token: token, blacklist: blacklist, limit: limit)
        authClient = Auth.new('ci', @token)
        print "Authentication with auth2 version #{authClient.version}"
        tokenInfo = authClient.token
        @username = tokenInfo['user']
    end

    def filter(workspaceInfo)
        if !isNarrative(workspaceInfo) 
            return false
        end

        owner = workspaceInfo[2]
        if owner != @username
            return false
        end

        return true
    end
end

indexer = OwnNarrativeIndexer.new
indexer.index
