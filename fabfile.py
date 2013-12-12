import os

from fabric.api import env, task, settings, run, cd, parallel, put

from fabtools import require, deb
from fabtools.python import virtualenv

from jinja2 import Environment, FileSystemLoader

env.project_path = (env.project_path
                    if env.project_path
                    else '/home/%s/%s/' % (env.user, env.project_name))
env.virtualenv_path = (env.virtualenv_path
                       if env.virtualenv_path
                       else os.path.join(env.project_path, 'venv'))
env.requirements_file = (env.requirements_file
                         if env.requirements_file
                         else '%s%s' % (env.project_path, 'requirements.txt'))
env.hosts = eval(env.hosts)


@task
def debian_install(packages):
    """
    Install packages for Debian
    packages is a string with packages' names
    example: 'nginx python-pip'
    """
    deb.install(packages.split(' '))


@task
def setup_postgresql(db_user, db_passwd):
    require.postgres.server()
    require.postgres.user(db_user, password=db_passwd, createdb=True)


@task
def create_virtualenv(virtualenv_path):
    """
    Create a virtualenv by the path given
    """
    run('virtualenv %s' % virtualenv_path)


@task
def requirements_install(requirements_file):
    """
    Pip install
    """
    run('pip install -q -r %s' % requirements_file)


@task
def pip_install(package):
    """
    Pip install
    """
    with virtualenv(env.virtualenv_path):
        run('pip install -q  %s' % package)


@task
def create_db(db_name):
    """
    Create database by the given name
    """
    run('createdb %s' % db_name)


@task
def start_project(project_name):
    run('django-admin.py startproject %s' % project_name)


@task
def start_app(app_name):
    run('python manage.py startapp %s' % app_name)


@task
def initialize_repo(repo_url):
    run('git init')
    create_git_ignore_file()
    run('git add -A')
    run('git commit -m "initial project version"')
    run('git remote add origin %s' % repo_url)
    run('git push -u origin master')


@task
def create_git_ignore_file():
    with open('./.gitignore', 'w') as output_file:
        output_file.write('*.pyc\n*.pyo\nvenv\n')


@task
def code_checkout(repo_url, directory):
    """
    git clone
    """
    run('git clone -q %s %s' % (repo_url, directory))


@task
def django_runserver(port_number):
    run('python manage.py runserver %s' % port_number)


@task
def django_syncdb():
    run('python manage.py syncdb --noinput')


@task
def django_migrate():
    run('python manage.py migrate')


@task
def create_uwsgi_conf():
    templateLoader = FileSystemLoader(searchpath="templates")
    template_env = Environment(loader=templateLoader)
    template = template_env.get_template('uwsgi.ini')

    uwsgi_params = {}
    uwsgi_params['chdir'] = '%s%s' % (env.project_path,
                                      env.django_project_name)
    uwsgi_params['django_project_name'] = env.django_project_name
    uwsgi_params['virtualenv_path'] = env.virtualenv_path
    uwsgi_params['processes'] = env.uwsgi_processes
    with open('./uwsgi.ini', 'w') as output_file:
        output_file.write(template.render(uwsgi_params))


@task
def run_uwsgi():
    with virtualenv(env.virtualenv_path):
        with cd('%s%s' % (env.project_path, env.django_project_name)):
            run('uwsgi uwsgi.ini')


@task
def create_nginx_conf():
    templateLoader = FileSystemLoader(searchpath="templates")
    template_env = Environment(loader=templateLoader)
    template = template_env.get_template('nginx.conf')

    nginx_params = {}
    nginx_params['django_project_path'] = '%s%s' % (env.project_path,
                                                    env.django_project_name)
    nginx_params['uwsgi_socket'] = '%s/%s' % (
        nginx_params['django_project_path'], env.django_project_name+'.sock')
    nginx_params['http_port'] = env.http_port
    nginx_params['server_name'] = env.server_name
    nginx_params['workers'] = env.nginx_workers
    # with open('./%s_nginx.conf' % env.project_name, 'w') as output_file:
    #     output_file.write(template.render(nginx_params))
    with open('./nginx.conf', 'w') as output_file:
        output_file.write(template.render(nginx_params))


@task
@parallel
def bootstrap():
    with settings(user='root'):
        debian_install(env.system_packages)
        setup_postgresql(env.db_user, env.db_passwd)
    code_checkout(env.repo_url, env.project_path)
    create_virtualenv(env.virtualenv_path)
    create_db(env.db_name)
    with virtualenv(env.virtualenv_path):
        requirements_install(env.requirements_file)
        with cd('%s%s' % (env.project_path, env.django_project_name)):
            django_syncdb()
            # django_migrate()
            django_runserver(env.port_number)


@task
@parallel
def deploy():
    create_nginx_conf()
    with settings(user='root'):
        debian_install(env.system_packages)
        setup_postgresql(env.db_user, env.db_passwd)
        # put('./%s_nginx.conf' % env.project_name, '/etc/nginx/sites-enabled')
        put('./nginx.conf', '/etc/nginx/')
        run('/etc/init.d/nginx restart')
    code_checkout(env.repo_url, env.project_path)
    create_virtualenv(env.virtualenv_path)
    create_db(env.db_name)
    with virtualenv(env.virtualenv_path):
        requirements_install(env.requirements_file)
        with cd('%s%s' % (env.project_path, env.django_project_name)):
            django_syncdb()
            # django_migrate()
            create_uwsgi_conf()
            put('./uwsgi.ini', 'uwsgi.ini')
            run('uwsgi uwsgi.ini')
