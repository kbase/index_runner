require './services'

def refdata_workspaces(token)
    client = Workspace.new('ci', token)
    # Get all readable workspaces. This includes public workspaces
    # which we'll filter below
    workspaces = client.list_workspace_info({})
    workspaces.each do |workspace_info|
        # [workspaceId, workspaceName, owner, moddate,
        #     maxObjId, userPermission, globalPermission,
        #     lockstat, workspaceMetadata] = workspace_info

        workspaceId = workspace_info[0]
        owner = workspace_info[2]
        globalPermission = workspace_info[6]
        metadata = workspace_info[8]

        # Filter for:
        # - public workspaces
        # - narratives (has narrative metadata key)
        # - saved narratives
        if metadata.has_key?('searchtags') && metadata['searchtags'].include?('refdata') 
            p("refdata workspace #{workspace_info}")
            next
        end
    end
end

def fetch_object_infos(token, workspaceId) 
    workspaceClient = Workspace.new('ci', token)
    workspaceClient.list_objects({
        ids: [workspaceId]
    })
end

def run_indexer(ref)
    p "Indexing... #{ref}"
    result = system('docker', 'exec', 'indexrunner', 'indexer_admin', 'reindex', '--ref', ref)
    if result
        p("  success!")
    else
        p("  error :(")
    end
end

def index_workspace_with_limit(token, workspaceId, start, limit)
    fetch_object_infos(token, workspaceId)[start..].take(limit).each do |obj_info|
        objectId = obj_info[0]
        objectRef = "#{workspaceId}/#{objectId}"
        run_indexer objectRef
    end
end

def index_workspace(workspaceId) 
    objectRef = "#{workspaceId}"
    run_indexer objectRef
end

def index_workspaces(token, workspaces, start=0, limit=false)
    workspaces.each do |workspaceId|
        if limit
            index_workspace_with_limit(token, workspaceId, start, limit)
        else
            index_workspace(workspaceId)
        end
    end
end

token =ENV['KBTOKEN']
p "Token: #{token}"
p "Args: #{ARGV}"
if ARGV.length == 0
    p 'Sorry, must provide a list of workspaces to index'
    exit 1
end

workspaces = ARGV[0].split(',').map {|x| x.to_i}
p "Workspaces #{workspaces}"

if ARGV.length > 1
    limit = ARGV[1].to_i
    p "Limit #{limit}"
else
    limit = false
    p "No Limit"
end

index_workspaces token, workspaces, 0, limit
# refdata_workspaces token