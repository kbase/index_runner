require './services'

# 5947 - an ncbi workspace created by Matt in 2016. Should be deleted.
# $blacklist = [5947, 6306, 6309]
$blacklist = []

def index_public_narrative_workspaces(token)
    client = Workspace.new('ci', token)
    # Get all readable workspaces. This includes public workspaces
    # which we'll filter below
    workspaces = client.list_workspace_info({})

    workspaces.each do |workspace_info|
        # [workspaceId, workspaceName, owner, moddate,
        #     maxObjId, userPermission, globalPermission,
        #     lockstat, workspaceMetadata] = workspace_info

        workspaceId = workspace_info[0]
        globalPermission = workspace_info[6]
        metadata = workspace_info[8]

        # Filter for:
        # - public workspaces
        # - narratives (has narrative metadata key)
        # - saved narratives
        if globalPermission != 'r' || !metadata.has_key?('narrative') || metadata['is_temporary'] == 'true'
            next
        end

        if $blacklist.include? workspaceId
            next
        end

        objectRef = "#{workspaceId}"
        result = system('docker', 'exec', 'indexrunner', 'indexer_admin', 'reindex', '--ref', objectRef)
        if result
            p("success! #{workspaceId}")
        else
            p("error :( #{workspaceId}")
        end
    end
end

token =ENV['KBTOKEN']
p "Token: #{token}"

index_public_narrative_workspaces token