from fabric.api import *
from fabric.contrib.project import rsync_project

import os


env.hosts = ['130.211.170.206'] #['159.203.170.25']
env.user = 'diepdt'#'root'
env.use_ssh_config = True
ROOT_DIR = os.path.dirname(__file__)


def update():
    remote_dir = 'projects'#'/root'
    rsync_project(local_dir=ROOT_DIR, remote_dir=remote_dir, exclude=['*.pyc', '.*', 'model/*', 'logs/*'], delete=True)
