import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from alembic.config import Config
from alembic import command
cfg = Config('alembic.ini')
command.current(cfg)
