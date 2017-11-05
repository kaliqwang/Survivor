#!/home/fijisurvivor/.virtualenvs/survivorenv/bin/python3.6

import os, sys, django

proj_path = "/home/fijisurvivor/Survivor"  # TODO: hardcoded

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Survivor.settings")
django.setup()
# sys.path.append(proj_path)
# os.chdir(proj_path)
#
# from django.core.wsgi import get_wsgi_application
# application = get_wsgi_application()

from django.core import management
management.call_command('check_game_start')
management.call_command('quota_check')
