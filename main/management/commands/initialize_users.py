from django.core.management.base import BaseCommand, CommandError

from main.models import *

import csv

from Survivor.settings import BASE_DIR

class Command(BaseCommand):
    help = 'Initialize users from user_data.csv file'

    def handle(self, *args, **options):
        num_deleted = User.objects.filter(is_superuser=False).all().delete()
        self.stdout.write(self.style.SUCCESS(str(num_deleted) + ' users deleted'))

        game = Game.objects.get_current()

        count = 0

        with open(os.path.join(BASE_DIR, 'user_data.csv'), newline='') as csvfile:
            lines = csv.reader(csvfile)
            next(lines)  # skip column headers
            for row in lines:
                full_name = row[0].split()
                first_name = full_name[0]
                last_name = full_name[1]
                codename = row[1]
                username = row[2]
                password = row[3]
                email = row[4]
                phone_num = row[5]

                user = User(first_name=first_name, last_name=last_name, username=username, password=password, email=email)
                user.save()
                user.profile.phone_num = phone_num
                user.profile.codename = codename
                user.profile.save()

                self.stdout.write(self.style.SUCCESS('New User: %s %s %s %s %s %s %s ' % (user.first_name, user.last_name, user.username, user.password, user.email, user.profile.phone_num, user.profile.codename)))

                if game:
                    game.add_player(user)

                count += 1

        self.stdout.write(self.style.SUCCESS(str(count) + ' users created'))