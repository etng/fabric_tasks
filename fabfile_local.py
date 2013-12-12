import os

from fabric.api import env, task, local, prefix, lcd

env.django_project_name = 'new_project'
env.django_app_name = 'new_app'
env.repo_url = 'https://github.com/tianyi33/fabric_presentation.git'
env.db_name = 'fabric_presentation'
env.requirement_file = 'requirements.txt'
env.project_path = os.path.abspath(os.path.dirname(__file__))
env.virtualenv_path = os.path.join(env.project_path, 'venv')


@task
def create_virtualenv():
    local('virtualenv %s' % env.virtualenv_path)


@task
def pip_install():
    with prefix('source %s/bin/activate' % env.virtualenv_path):
        local('pip install -r %s' % env.requirement_file)


@task
def create_db():
    local('createdb %s' % env.db_name)


@task
def start_project():
    with prefix('source %s/bin/activate' % env.virtualenv_path):
        local('django-admin.py startproject %s' % env.django_project_name)


@task
def start_app():
    with lcd('%s/%s' % (env.project_path, env.django_project_name)):
        with prefix('source %s/bin/activate' % env.virtualenv_path):
            local('python manage.py startapp %s' % env.django_app_name)


@task
def initialize_repo():
    local('git init')
    create_git_ignore_file()
    local('git add -A')
    local('git commit -m "initial project version"')
    local('git remote add origin %s' % env.repo_url)
    local('git push -u origin master')


@task
def create_git_ignore_file():
    with open('./.gitignore', 'w') as output_file:
        output_file.write('*.pyc\n*.pyo\nvenv\n')


@task
def bootstrap():
    create_virtualenv()
    pip_install()
    create_db()
    start_project()
    start_app()
    initialize_repo()
