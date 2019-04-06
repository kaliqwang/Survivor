from django.core.management.base import BaseCommand, CommandError

from main.models import *


class Command(BaseCommand):
    help = 'Eliminate players who have not met their quota'

    def handle(self, *args, **options):
        game = Game.objects.get_current()
        if game:
            game.randomize_player_sequence()
        else:
            self.stdout.write(self.style.SUCCESS('Current game not found'))