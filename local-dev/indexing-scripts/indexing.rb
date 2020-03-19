$blacklist = [5947, 6306, 6309]

$defaultBlacklist = {
    'ci' => [5947, 6306, 6309],
    'next' => nil,
    'appdev' => nil,
    'prod' => nil
}

class Indexer
    def initialize(token: nil, blacklist: nil, limit: nil, env: nil)
        if token == nil
            token = ENV['TOKEN']
            if token == nil 
                raise 'Error: TOKEN env variable is required'
            end
        end
        puts "Token: #{token}"

        if env == nil
            env = ENV['KBASE_ENV']
            if env == nil 
                env = 'ci'
            end
        end
        puts "Env: #{env}"

        if limit == nil
            limit = ENV['LIMIT']
            if limit != nil
                limit = limit.to_i
            end
        end
        puts "Limit: #{limit}"

        if blacklist == nil
            blacklist = $defaultBlacklist[env]
            if blacklist == nil
                blacklist = []
            end
        end

        @token = token
        @blacklist = blacklist
        @limit = limit
        @env = env
    end

    def run_indexer(ref)
        puts
        puts "Indexing... #{ref}"
        result = system('docker', 'exec', 'indexrunner', 'indexer_admin', 'reindex', '--ref', ref)
        if result
            puts "  success!"
        else
            puts "  error :("
        end
    end

    def filter(workspaceInfo) 
        raise "'filter' NOT IMPLEMENTED (abstract method)"
    end

    def isNarrative(workspaceInfo)
        metadata = workspaceInfo[8]
        if !metadata.has_key?('narrative') 
            return false
        end
        
        if metadata['is_temporary'] == 'true' 
            return false
        end

        return true
    end

    def isBlacklisted(workspaceInfo) 
        if @blacklist.include? workspaceInfo[0]
            return true
        end

        return false
    end

    def isRefdata(workspaceInfo) 
        metadata = workspaceInfo[8]
        searchTags = metadata['searchtags']
        if searchTags == nil
            return false
        end
        searchTags.include? 'refdata'
    end

    def isPublic(workspaceInfo) 
        globalPermission = workspaceInfo[6]
        globalPermission == 'r'
    end

    def isMetadata(workspaceInfo, key, value) 
        metadata = workspaceInfo[8]
        possibleValue = metadata[key]
        if possibleValue == nil
            return false
        end
        possibleValue == value
    end

    def isNarratorial(workspaceInfo)
        metadata = workspaceInfo[8]
        if metadata['narratorial'] == nil 
            return false
        end
        if metadata['narratorial'] == '1'
            return true
        end
    end

    def index()
        client = Workspace.new('ci', @token)
        # Get all readable workspaces. This includes public workspaces
        # which we'll filter below
        workspaces = client.list_workspace_info({})

        indexedCount = 0
        workspaces.each do |workspaceInfo|
            break if @limit && indexedCount > @limit
            next if isBlacklisted(workspaceInfo)
            next if !filter(workspaceInfo)

            index_workspace(workspaceInfo[0])
            indexedCount += 1
        end
    end

    def index_workspace_objects(object_limit: nil)
        client = Workspace.new('ci', @token)
        # Get all readable workspaces. This includes public workspaces
        # which we'll filter below
        workspaces = client.list_workspace_info({})

        workspaceCount = 0
        workspaces.each do |workspaceInfo|
            break if @limit && workspaceCount > @limit
            next if isBlacklisted(workspaceInfo)
            next if !filter(workspaceInfo)
            
            objects = client.list_objects({
                'ids': [workspaceInfo[0]]
            })

            indexedCount = 0
            objects.each do |objectInfo|
                break if object_limit && indexedCount >= object_limit

                index_object(workspaceInfo[0], objectInfo[0])
                indexedCount += 1
            end
        end
    end
    
    def index_workspace(workspaceId) 
        objectRef = "#{workspaceId}"
        run_indexer objectRef
    end

    def index_object(workspaceId, objectId) 
        objectRef = "#{workspaceId}/#{objectId}"
        run_indexer objectRef
    end
end
