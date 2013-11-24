from fabric.api import env, task, settings, run, cd
from fabric.contrib.files import exists, append
from fabtools import require, deb, arch
from fabtools.python import virtualenv, install_requirements
from fabtools.require import postgres

import server_conf

env.hosts = server_conf.HOSTS
env.user = server_conf.USER if server_conf.USER else env.user
env.system_packages = (server_conf.SYSTEM_PACKAGES_NEEDED
                       if server_conf.SYSTEM_PACKAGES_NEEDED else '')
env.project_name = (server_conf.PROJECT_NAME
                    if server_conf.PROJECT_NAME else '')
env.repo_url = (server_conf.REPO_URL
                if server_conf.REPO_URL else '')
env.db_name = (server_conf.DB_NAME
               if server_conf.DB_NAME else '')
env.db_user_name = (server_conf.DB_USER
                    if server_conf.DB_USER else '')
env.db_password = (server_conf.DB_PASSWORD
                   if server_conf.DB_PASSWORD else '')
env.requirement_file = (server_conf.REQUIREMENT_FILE
                        if server_conf.REQUIREMENT_FILE else '')
env.project_path = (server_conf.PROJECT_PATH
                    if server_conf.PROJECT_PATH
                    else '/home/%s/%s/' % (env.user, env.project_name))
env.virtualenv_path = (server_conf.VIRTUALENV_PATH
                       if server_conf.VIRTUALENV_PATH
                       else '%svirutal_env_%s'
                       % (env.project_path, env.project_name))


@task
def bootstrap_debian():
    debian_install(env.system_packages)
    with cd('/home/%s' % env.user):
        create_directories(env.project_name)

    with cd(env.project_path):
        svn_check_out(env.repo_url)

    create_virtualenv(env.virtualenv_path)

    with virtualenv(env.virtualenv_path):
        install_requirements(env.project_path+env.requirement_file)

    with settings(user='root'):
        postgres.server()
        require.postgres.user(env.user, password=env.user)
        postgres.database(env.db_name, owner=env.user)

    with cd(env.project_path):
        with virtualenv(env.virtualenv_path):
            run('python manage.py syncdb')
            run('python manage.py migrate')


@task
def bootstrap_arch():
    arch_install(env.system_packages)


@task
def create_directories(directories_names):
    """
    Create directories
    directory_names is a string with directories' names
    example: 'project1 project2'
    """
    directories = directories_names.split(' ')
    for directory in directories:
        run('mkdir %s' % directory)


@task
def svn_check_out(repo_url):
    run('svn co %s .' % repo_url)


@task
def set_up_virtualenvwrapper():
    with settings(user='root'):
        run('pip install %s' % 'virtualenvwrapper')

    with cd('/home/%s' % env.user):
        virtualenvwrapper_config = """%s\n%s\n%s""" % (
            'export WORKON_HOME=$HOME/.virtualenvs',
            'export VIRTUALENVWRAPPER_SCRIPT=\
            /usr/local/bin/virtualenvwrapper.sh',
            'source /usr/local/bin/virtualenvwrapper_lazy.sh')
        append('.bash_profile', virtualenvwrapper_config)


@task
def create_virtualenv(virtualenv_path):
    require.python.virtualenv(virtualenv_path)


@task
def create_virtualenv_using_virutalenvwrapper(virtualenv_name):
    """
    Create a virtualenv for the project.
    If the virtualenv is already exists, it will not be created again
    """
    with settings(warn_only=True):
        result = run('workon %s' % virtualenv_name)

    if not result.succeeded:
        if virtualenv_name:
            run('mkvirtualenv %s' % virtualenv_name)
        else:
            print ('No virtualenv name provided...')


@task
def set_up_screen():
    """Set up screenrc if not yet"""
    with cd('/home/%s' % env.user):
        if not exists('.screenrc'):
            screen_config_text = """%s\n%s\n\n%s """ % (
                'hardstatus alwayslastline',
                'hardstatus string \'%{= kG}[ %{G}%H %{g}][%= %{=kw}%?%-Lw%?%{r}(%{W}%n*%f%t%?(%u)%?%{r})%{w}%?%+Lw%?%?%= %{g}][%{B}%Y-%m-%d %{W}%c %{g}]\'',
                'defscrollback 6000')
            append('.screenrc', screen_config_text)


@task
def debian_install(packages):
    """
    Install packages for Debian
    packages is a string with packages' names
    example: 'nginx python-pip'
    """

    with settings(user='root'):
        deb.install(packages.split(' '))


@task
def debian_uninstall(packages):
    """
    Uninstall packages for Debian
    packages is a string with packages' names
    example: 'nginx python-pip'
    """

    with settings(user='root'):
        deb.uninstall(packages.split(' '))


@task
def arch_install(packages):
    """
    Install packages for Arch
    packages is a string with packages' names
    example: 'nginx python-pip'
    """
    with settings(user='root'):
        arch.install(packages.split(' '))


@task
def arch_uninstall(packages):
    """
    Uninstall packages for Arch
    packages is a string with packages' names
    example: 'nginx python-pip'
    """
    with settings(user='root'):
        arch.uninstall(packages.split(' '))
