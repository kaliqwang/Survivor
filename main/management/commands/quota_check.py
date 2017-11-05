from django.core.management.base import BaseCommand, CommandError

from main.models import *


class Command(BaseCommand):
    help = 'Eliminate players who have not met their quota'

    def handle(self, *args, **options):
        game = Game.objects.get_current()
        if game:
            quota_check = game.do_quota_check()
            if quota_check:
                self.stdout.write(self.style.SUCCESS('Successfully performed quota check'))
            else:
                self.stdout.write(self.style.SUCCESS('Next quota check is on' + game.date_next_quota_check))
        else:
            self.stdout.write(self.style.SUCCESS('Current game not found'))