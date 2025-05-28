import gitlab
from gitlab.exceptions import GitlabError
from loguru import logger

class GitLabClient:
    def __init__(self, url: str):
        self.url = url
    
    @logger.catch
    def create_merge_request(self, project_id: str, token: str, data: Dict) -> str:
        gl = gitlab.Gitlab(self.url, private_token=token)
        
        try:
            project = gl.projects.get(project_id)
            branch = project.branches.create({
                'branch': data['branch_name'],
                'ref': data['base_branch']
            })
            
            commit_actions = [{
                'action': 'create',
                'file_path': file_path,
                'content': content
            } for file_path, content in data['files'].items()]
            
            commit = project.commits.create({
                'branch': data['branch_name'],
                'commit_message': data['commit_message'],
                'actions': commit_actions
            })
            
            mr = project.mergerequests.create({
                'source_branch': data['branch_name'],
                'target_branch': data['base_branch'],
                'title': data['title'],
                'description': data['description']
            })
            
            return mr.web_url
            
        except GitlabError as e:
            logger.error(f"GitLab Error: {e.error_message}")
            raise