from django.core.management.base import BaseCommand, CommandError

from main.models import *


class Command(BaseCommand):
    help = 'Start game if start date has been reached'

    def handle(self, *args, **options):
        game = Game.objects.get_current()
        if game:
            if date.today() <= game.date_start:
                if game.has_started:
                    self.stdout.write(self.style.SUCCESS('Game has already started'))
                else:
                    if game.start():
                        self.stdout.write(self.style.SUCCESS('Game has started!'))
                    else:
                        self.stdout.write(self.style.SUCCESS('Cannot start game with less than 2 players'))
            else:
                self.stdout.write(self.style.SUCCESS('Game start date is set to ' + str(game.date_start)))
        else:
            self.stdout.write(self.style.SUCCESS('Current game not found'))