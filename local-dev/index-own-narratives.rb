require './services'

$blacklist = []

def index_user_narrative_workspaces(token, username)
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
        if !metadata.has_key?('narrative') || metadata['is_temporary'] == 'true' || owner != username
            p("skipping workspace #{workspaceId} for owner #{owner}")
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
username =ENV['KBUSERNAME']

p "Token: #{token}"
p "Username: #{username}"

index_user_narrative_workspaces token, username