require './services'

def refdata_workspaces(token)
    workspaces = 

def index_workspaces(token, workspaces)
    workspaces.each do |workspaceID|
        objectRef = "#{workspaceID}"
        result = system('docker', 'exec', 'indexrunner', 'indexer_admin', 'reindex', '--ref', objectRef)
        if result
            p("success! #{workspaceID}")
        else
            p("error :( #{workspaceID}")
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

index_workspaces token, workspaces