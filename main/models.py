import os
from datetime import date, timedelta
from urllib.parse import urlparse

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.core.mail import send_mass_mail, send_mail
from django.core.validators import RegexValidator
from django.db import models

# Twilio
from django.db.models import Case, Count, Max
from django.db.models import F
from django.db.models import When
from django.db.models.signals import post_save
from django.dispatch import receiver
from twilio.rest import Client

# TODO: favicon for website

# TODO: ask ben to customize text notification messages

# TODO: state in rules that players should get a text nofication whenever they submit that they eliminated a player. If they don't get a notification, they should submit again.

# TODO: provide an error message to player if their elimination submission failed / something went wrong

# TODO: when logged in as admin, show list of eliminations - and allow admin to click "undo" next to an elimination. Clicking this opens a dialog that displays a list of dependencies (e.g. eliminations that will also need to be undone as a result) to confirm. Admin can then click "proceed" or "cancel".

# TODO: ask ben: do we need to prevent people from making duplicate accounts (e.g. giving themselves extra lives)? probably not right? since if someone gets killed, but then later ends up winning, the original attacker will come forward?
# we could though - by enforcing unique phone-numbers?

# TODO: ask ben: send text notification to admin every time elimination occurs?

# TODO: cannot undo elimination once game has ended

# TODO: terminology: kill vs elimination, alive vs active, dead vs inactive, num_kills vs num_eliminations, etc.
# TODO: terminology: reset vs revive vs revert vs revert, etc.

# TODO: make sure that multiple spammed requests don't break the app (e.g. what happens if admin user spams "start_game" a bunch of times?)

# TODO: does django handle multiple requests simultaneously/asynchronously? If so, need to recheck everything to make sure thread-safe

# TODO: refactor - consolidate multiple functions into single function

# TODO: messaging - send email/text messages to Ben

# TODO: jQuery confirmation dialogs for everything

# TODO: display message to user: quota check every 5 days or something

# TODO: add simple confirmation page for most buttons (e.g. target eliminate, cancel game, etc.)

# TODO: idea: display a timer in the navbar for the global game timer (e.g. how much time has elapsed in the game already - days? weeks? months? etc.) - would be kind of cool; search for a jQuery clock plugin

# TODO: double check when things can be done; e.g. eliminations cannot be reverted once a game has ended or closed

# TODO: in HTML, replace all <br> elements with proper margins/padding

# TODO: fix timezone-aware issues (e.g. on confirm revert elimination page - make sure timestamp is correct)

# TODO: favicon doesn't work

# TODO: post useful information to the admin user about Twilio (e.g., pricing at $0.0075 per text notification; around 4 (or however many) notifications expected per player; so $20 can support ___ players, $30 can support ___ players, etc. etc.). Allow admin to customize what kinds of notifications are sent (based on how much he plans to charge to his account). He can choose bare minimum notifications (e.g. approx 4 notifications sent per player). Or he can choose to also enable optional "reminder" messages to people periodically. Etc. etc.

# RULES: Once there are 10 players left, players kill their targets by marking their skin with permanent marker. Players also have the ability to defend themselves against their attackers by marking their attackers back.
# RULES: Once there are only 2 players left, the quota checks will stop, and the last two players will have to fight it out, as long as it takes, to win the game.

from Survivor import settings

EMAIL_SUBJECT_LINE = 'FIJI Survivor'
EMAIL_FROM_ADDRESS = 'fijisurvivor@gmail.com'
MESSAGE_HEADER = '---- FIJI Survivor ---- '  # TODO Ben
DEFAULT_REGISTRATION_PERIOD_DAYS = 7  # TODO: 1 week for signup by default
DEFAULT_QUOTA_PERIOD_DAYS = 7  # TODO: number of days per quota check; players need to get at least 1 kill every 7 days by default

GAME_START_MESSAGE = "The game has started! Your target is %s. Stay safe, have fun, and good luck!"  # TODO: display initial target name
GAME_END_MESSAGE = "The game has ended. See the website for more info."
GAME_CANCELLED_MESSAGE = "The game has been cancelled by an admin. Please check the website for more details."

url_validator = RegexValidator(regex=r'^(http(s)?://)?([\w-]+\.)+[\w-]+[.com]+(/[/?%&=]*)?$', message='Must be a valid URL')
phone_validator = RegexValidator(regex=r'^\d{10}$', message="Must be a 10 digit phone number")
tas_validator = RegexValidator(regex=r'^[a-zA-Z0-9]{34}$', message='Must be a 34 digit alphanumeric string')
tat_validator = RegexValidator(regex=r'^[a-z0-9]{32}$', message='Must be a 32 digit lowercase alphanumeric string')


def default_start_date():
    return date.today() + timedelta(days=DEFAULT_REGISTRATION_PERIOD_DAYS)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance=None, created=False, **kwargs):
    if created:
        user_profile = UserProfile(user=instance)
        user_profile.save()


class GetOrNoneManager(models.Manager):

    def get_or_none(self, **kwargs):
        try:
            return self.get(**kwargs)
        except self.model.DoesNotExist:
            return None


class GameManager(models.Manager):

    def get_current(self):
        try:
            return self.filter(has_closed=False).first()
        except self.model.DoesNotExist:
            return None


class SingletonModel(models.Model):

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SingletonModel, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    phone_num = models.CharField(validators=[phone_validator], max_length=10)  # TODO: unique=True
    codename = models.CharField(max_length=50)
    # image_url = models.URLField('Image URL')

    def __str__(self):
        return self.user.first_name + " " + self.user.last_name + "'s profile"


class Game(models.Model):
    # Game settings
    admin = models.ForeignKey(User, related_name='games_as_admin', on_delete=models.CASCADE)
    date_start = models.DateField(default=default_start_date, help_text='Game starts at midnight')
    date_end = models.DateField(blank=True, null=True)
    date_close = models.DateField(blank=True, null=True)
    date_last_quota_check = models.DateField(blank=True, null=True)
    quota_period_days = models.IntegerField(default=DEFAULT_QUOTA_PERIOD_DAYS)
    # Game status
    has_started = models.BooleanField(default=False)  # indicates game has been started
    has_ended = models.BooleanField(default=False)  # indicates game has ended normally (e.g. has been won)
    has_closed = models.BooleanField(default=False)  # indicates game has been closed
    details = models.TextField(blank=True)
    # Twilio
    twilio_phone_num = models.CharField('Twilio Phone Number', validators=[phone_validator], max_length=10)
    twilio_account_sid = models.CharField('Twilio Account SID', validators=[tas_validator], max_length=34)
    twilio_auth_token = models.CharField('Twilio Authorization Token', validators=[tat_validator], max_length=32)

    objects = GameManager()

    def __init__(self, *args, **kwargs):
        super(Game, self).__init__(*args, **kwargs)
        self.client = None
        if self.twilio_account_sid and self.twilio_auth_token:
            self.client = Client(self.twilio_account_sid, self.twilio_auth_token)

    def __str__(self):
        return "Game " + str(self.pk)

    def clean(self):
        if self.date_start and (self.date_start <= date.today()):
            raise ValidationError(_('Start date must be in the future.'))

    @property
    def length(self):
        return ((self.date_end if self.has_ended else date.today()) - self.date_start).days

    @property
    def players_ordered(self):  # TODO: redundant now that ordering is specified in Player class meta?
        return self.players.order_by('position')

    @property
    def players_alive(self):
        return self.players.filter(alive=True)

    @property
    def players_dead(self):
        return self.players.filter(alive=False)

    @property
    def players_alive_ordered(self):
        return self.players.filter(alive=True).order_by('position')

    @property
    def players_dead_ordered(self):
        return self.players.filter(alive=False).order_by('position')

    @property
    def players_ordered_by_num_kills_decreasing(self):
        players = self.players_ordered
        for p in players:
            p.sync_num_kills()
        return self.players.order_by('-num_kills_copy')

    @property
    def num_players(self):
        return self.players.count()

    @property
    def num_alive(self):
        return self.players_alive.count()

    @property
    def num_dead(self):
        return self.players_dead.count()

    @property
    def date_next_quota_check(self):
        return (self.date_last_quota_check if self.date_last_quota_check else self.date_start) + timedelta(days=self.quota_period_days)

    @property
    def first_place(self):
        return self.players.filter(alive=True).first() if self.has_ended else None

    @property
    def second_place(self):
        return self.eliminations.filter(valid=True).first().target if self.has_ended else None

    @property
    def third_place(self):
        return self.eliminations.filter(valid=True)[1].target if (self.has_ended and (self.num_players > 2)) else None  # TODO: edge case

    @property
    def most_kills(self):  # NOTE: undefined behavior if not game.has_ended # TODO: clean/fix this
        if self.has_ended:
            players = self.players_ordered_by_num_kills_decreasing
            most_kills = players.first().num_kills_copy
            return players.filter(num_kills_copy=most_kills).all()

    def add_player(self, user):
        return Player.objects.create(game=self, user=user) if not self.has_started else None

    def remove_player(self, user):
        player = user.players.get_or_none(game=self)
        return player.delete() if player else None

    def initialize_player_sequence(self):
        players = list(self.players.order_by('?'))
        last = len(players) - 1
        for i in range(0, last):
            players[i].position = i
            players[i].target = players[i+1]
            players[i].save()
        players[last].position = last
        players[last].target = players[0]
        players[last].save()

    def start(self):
        if self.num_players > 1:  # NOTE: cannot start a war with less than two players
            self.initialize_player_sequence()
            self.date_start = date.today()  # NOTE: override
            self.has_started = True
            self.details = "Game is in progress"
            self.save()
            for p in self.players.all():
                self.send_message(p, GAME_START_MESSAGE % p.target)
            return True
        return False

    def do_check_end(self):
        if self.num_alive == 1:
            self.end()
            return True
        return False

    def end(self):
        self.date_end = date.today()
        self.has_ended = True
        self.details = "Game ended normally"
        self.save()
        self.send_mass_message(self.players.all(), GAME_END_MESSAGE)

    def close(self):
        self.date_close = date.today()
        self.has_closed = True
        self.save()
        if not self.has_ended:
            self.details = "Game was cancelled"
            self.save()
            self.send_mass_message(self.players.all(), GAME_CANCELLED_MESSAGE)

    # TODO: make sync-safe with server state
    def do_quota_check(self):  # TODO: link this to admin commands / management commands  # TODO: refactor: do_quota_check should unconditionally perform the quota check, create a new quota_check() method to wrap
        if self.num_alive > 2 and date.today() >= self.date_next_quota_check:  # TODO: quota check rule
            players = self.players_alive_ordered
            quota_met_count = 0
            for p in players:
                if p.quota_met:
                    quota_met_count += 1
            if quota_met_count >= 2:  # TODO: shortcut by testing of quota_met_count is the same as len(players) - thus no quota check needed
                self.date_last_quota_check = date.today()
                self.save()
                return QuotaCheck.objects.create(game=self)
        return None

    def send_message(self, player, message):
        if player.user.profile.phone_num:
            try:
                self.client.messages.create(to=player.user.profile.phone_num, from_=self.twilio_phone_num, body=MESSAGE_HEADER+message)
            except Exception as e:
                print(e)  # TODO: log error
        if player.user.email:
            send_mail(EMAIL_SUBJECT_LINE, message, EMAIL_FROM_ADDRESS, [player.user.email], fail_silently=True)

    def send_mass_message(self, players, message):
        message_list = []
        for player in players:
            if player.user.profile.phone_num:
                try:
                    self.client.messages.create(to=player.user.profile.phone_num, from_=self.twilio_phone_num, body=MESSAGE_HEADER+message)
                except Exception as e:
                    print(e)  # TODO: log error
            if player.user.email:
                send_mail(EMAIL_SUBJECT_LINE, message, EMAIL_FROM_ADDRESS, [player.user.email], fail_silently=True)
                print(player.user.email)
        #         message = (EMAIL_SUBJECT_LINE, message, EMAIL_FROM_ADDRESS, [player.user.email])
        #         message_list.append(message)
        # send_mass_mail(tuple(message_list), fail_silently=True)  # TODO: send_mail() works but send_mass_mail() doesn't; why? https://docs.djangoproject.com/en/1.11/topics/email/#django.core.mail.send_mail

    def send_message_to_admin(self, message):  # TODO: temp
        send_mail(EMAIL_SUBJECT_LINE, message, EMAIL_FROM_ADDRESS, [self.admin.email], fail_silently=True)


def get_current_game():
    return Game.objects.get_current()


class Player(models.Model):
    game = models.ForeignKey(Game, related_name='players', default=get_current_game, on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='players', on_delete=models.CASCADE)
    position = models.IntegerField(default=-1)
    target = models.OneToOneField('self', related_name='attacker', blank=True, null=True)
    num_kills_prev_quota_check = models.IntegerField(default=0)
    num_kills_copy = models.IntegerField(default=0)
    exempt_from_quota_check = models.BooleanField(default=False)
    alive = models.BooleanField(default=True)  # TODO: sync-safe vs performance

    objects = GetOrNoneManager()

    class Meta:
        ordering = ('-game', 'position',)
        unique_together = ('game', 'user')

    def __str__(self):
        return self.user.first_name + " " + self.user.last_name

    @property
    def dead(self):
        return not self.alive

    @property
    def elimination_as_target(self):
        return self.eliminations_as_target.get(valid=True) if not self.alive else None

    @property
    def killer(self):
        return self.elimination_as_target.killer if self.alive else None  # TODO: currently returns None if player was killed by their target in self defense; fix this

    @property
    def date_of_death(self):
        return self.elimination_as_target.timestamp if self.alive else None

    @property
    def num_kills(self):
        return self.eliminations_as_attacker.filter(quota_check=None).filter(valid=True).filter(is_reverse=False).count() # TODO: performance  # TODO: game semantics: does num_kills count self-defense kills? CURRENTLY NOT

    @property
    def num_kills_this_quota(self):
        return self.num_kills - self.num_kills_prev_quota_check

    @property
    def quota_met(self):  # TODO: optimize performance
        return self.exempt_from_quota_check or (self.num_kills_this_quota > 0)

    def sync_num_kills(self):
        self.num_kills_copy = self.num_kills
        self.save()

    def eliminate_target(self):
        return self.target.eliminate()

    def eliminate_attacker(self):
        return self.attacker.eliminate(is_reverse=True)

    # returns elimination object if elimination occurred, else None
    # TODO: make sync-safe with server state
    def eliminate(self, is_reverse=False):
        return Elimination.objects.create(game=self.game, target=self, is_reverse=is_reverse) if (self.alive and (self.attacker.pk != self.pk)) else None  # TODO: check duplicate eliminations in save() method?

    # returns number of eliminations reverted
    def revive(self):
        # TODO: make sync-safe with server state
        return self.elimination_as_target.revert() if self.alive else 0

ELIMINATED_BY_QUOTA_CHECK_MESSAGE = "You have been eliminated by for not meeting the quota."
TARGET_ELIMINATED_BY_QUOTA_CHECK_MESSAGE = "Your target has been eliminated for not meeting the quota. Your new target is %s."

ELIMINATED_BY_ATTACKER_MESSAGE = "You have been eliminated by %s."
TARGET_ELIMINATED_BY_ATTACKER_MESSAGE = "Congratulations on eliminating %s. Your new target is %s."

ELIMINATED_BY_TARGET_MESSAGE = "You have been eliminated by your target %s in self defense."
TARGET_ELIMINATED_BY_TARGET_MESSAGE = "Your target (%s) has been eliminated by their target in self defense. Your new target is %s"
ATTACKER_ELIMINATED_BY_TARGET_MESSAGE = "Congratulations on eliminating %s in self defense."

REVIVED_BY_ADMIN_MESSAGE = "You have been revived by an admin."
TARGET_REVIVED_BY_ADMIN_MESSAGE = "Your elimination of %s was reverted by an admin. Your new target is %s."

# TODO: MAJOR ASSUMPTION (HOW TO UPHOLD THIS ASSUMPTION): Eliminations due to QuotaChecks occur in an uninterrupted sequence (e.g. primary keys increase by one). Thus, the sequence of eliminations looks something like:
# ne -> ne -> ne -> qc -> qc -> qc -> qc -> qc -> ne -> ne -> ne -> ne ....
# where ne is "normal elimination" and qc is "quota check" elimination
# TODO: DISALLOW ELIMINATIONS TO BE SUBMITTED WHILE A QUOTA CHECK IS GOING ON. FIRST STEP OF QUOTA CHECK - SET SOME SYSTEM STATUS VARIABLE IN DATABASE THAT PREVENTS NEW ELIMINATIONS FROM BEING CREATED.


class QuotaCheck(models.Model):
    game = models.ForeignKey(Game, related_name='quota_checks', default=get_current_game, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    valid = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.pk:  # TODO: only on creation?
            for p in self.game.players_alive_ordered:
                if p.quota_met:
                    p.num_kills_prev_quota_check = self.num_kills
                    p.save()
                else:
                    Elimination.objects.create(game=self.game, quota_check=self, target=p)  # TODO: check duplicate eliminations in save() method?
        super(QuotaCheck, self).save(*args, **kwargs)

    def revert(self, revert_dependencies=True):  # TODO: reverting this quotacheck, means that all future quota checks need to be reverted too; or just make it so that only the most recent quota check is allowed to be reverted?
        num_reverted = 0
        if self.valid:
            if revert_dependencies:
                quota_checks = self.game.quota_checks.filter(valid=True).filter(timestamp__gt=self.timestamp).order_by('-pk').all()  # TODO: in reverse order of occurrence
                for qc in quota_checks:
                    num_reverted += qc.revert(revert_dependencies=False)
            # INVARIANT: all quota checks that come after this one have been reverted
            for e in self.eliminations.order_by('-pk').all():
                num_reverted += e.revert_helper(revert_quota_check_dependencies=False)
        return num_reverted


class Elimination(models.Model):
    game = models.ForeignKey(Game, related_name='eliminations', default=get_current_game, on_delete=models.CASCADE)  # TODO: redundant; players already store game information
    quota_check = models.ForeignKey(QuotaCheck, related_name='eliminations', blank=True, null=True)
    attacker = models.ForeignKey(Player, related_name='eliminations_as_attacker')
    target = models.ForeignKey(Player, related_name='eliminations_as_target')
    is_reverse = models.BooleanField(default=False)  # NOTE: e.g. self.target was eliminated by self.target.target, not self.attacker
    timestamp = models.DateTimeField(auto_now_add=True)
    valid = models.BooleanField(default=True)

    class Meta:
        ordering = ('-pk',)

    def __str__(self):
        return str(self.game) + ": " + self.killer_name + " -> " + str(self.target)

    @property
    def from_quota_check(self):
        return self.quota_check is not None

    @property
    def killer(self):
        return None if (self.quota_check or self.is_reverse) else self.attacker  # TODO: currently returns None if reverse elimination (target killed by target rather than attacker); implement way to track target

    @property
    def killer_name(self):
        return str(self.killer) if self.killer else "Quota check"

    def clean(self):
        if self.attacker.pk == self.target.pk:
            raise ValidationError(_('Attacker and target cannot be the same player'))
        if self.from_quota_check and self.is_reverse:
            raise ValidationError(_('Elimination due to quota check cannot be a reverse elimination'))

    def save(self, *args, **kwargs):
        if not self.pk:  # TODO: only on creation?
            self.attacker = self.target.attacker
            self.attacker.target = self.target.target
            self.target.target = None
            self.target.alive = False
            self.target.save()
            self.attacker.save()
            if self.from_quota_check:
                self.game.send_message(self.target, ELIMINATED_BY_QUOTA_CHECK_MESSAGE)
                self.game.send_message(self.attacker, TARGET_ELIMINATED_BY_QUOTA_CHECK_MESSAGE % self.target.target)  # TODO: Player.__str__() automatically called? CONFIRMED: IT DOES CONVERT TO STRING; NO WORRIES
            elif self.is_reverse:
                self.game.send_message(self.target, ELIMINATED_BY_TARGET_MESSAGE % self.attacker.target)
                self.game.send_message(self.attacker, TARGET_ELIMINATED_BY_TARGET_MESSAGE % (self.target, self.attacker.target))
                self.game.send_message(self.attacker.target, ATTACKER_ELIMINATED_BY_TARGET_MESSAGE % self.target)
            else:
                self.game.send_message(self.target, ELIMINATED_BY_ATTACKER_MESSAGE % self.attacker)
                self.game.send_message(self.attacker, TARGET_ELIMINATED_BY_ATTACKER_MESSAGE % (self.target, self.attacker.target))
            self.game.do_check_end()  # TODO NOTE: quota checks should not be able to end the game
        super(Elimination, self).save(*args, **kwargs)

    @property
    def num_dependencies(self):
        return 0  # TODO: return the number of dependent eliminations that would need to be reverted by self.revert() without actually having to call self.revert()

    # TODO: make sure e.revert_helper is never called directly outside of this class
    def revert_helper(self, revert_dependencies=True, revert_quota_check_dependencies=True):  # TODO: revert_helper means no need to check for future eliminations due to quota checks (none, or all reverted/invalidated already)
        num_reverted = 0
        if self.valid:
            num_reverted = 1
            print(TARGET_ELIMINATED_BY_QUOTA_CHECK_MESSAGE % self.target)  # TODO: remove
            # check for dependencies
            if revert_dependencies:
                if revert_quota_check_dependencies:
                    quota_checks = self.game.quota_checks.filter(timestamp__gt=self.timestamp).order_by('-pk').all()
                    for qc in quota_checks:
                        num_reverted += qc.revert(revert_dependencies=False)
                # INVARIANT: all quota_checks that come after this elimination have been reverted
                to_revert = []
                eliminations = self.game.eliminations.filter(valid=True).filter(pk__gt=self.pk).order_by('pk').all()  # TODO: in order of occurrence
                for e in eliminations:
                    # NOTE: self.from_quota_check CAN be true here; but for all e, e.from_quota_check MUST be false here - all future quota check eliminations should have been reverted/invalidated by this point
                    if e.attacker.pk == self.attacker.pk:  # TODO: ensure that the original self.target.target is alive: revert all eliminations e where e.attacker is self.attacker (attacker guaranteed not null - because any quota_checks in the future have been reverted at this point)
                        to_revert.append(e)
                    elif e.target.pk == self.attacker.pk:  # TODO: ensure that the original self.attacker is alive: if self.attacker was eliminated, revive him (e.g. revert that elimination); again - guaranteed not to have been eliminated by quota check at this point (e.g. attacker null)
                        num_reverted += e.revert_helper(revert_quota_check_dependencies=False)
                        break
                for e in reversed(to_revert):
                    num_reverted += e.revert_helper(revert_dependencies=False, revert_quota_check_dependencies=False)
            # INVARIANT: original self.attacker is alive, original self.target.target is alive, and original self.attacker.target is self.target.target now can revert this elimination
            # revert elimination
            target = Player.objects.get(pk=self.target.pk)  # NOTE: force reload updated object from database
            attacker = Player.objects.get(pk=self.attacker.pk)  # NOTE: force reload updated object from database

            print("Target: " + str(target.pk))
            print("Attacker: " + str(attacker.pk))
            print("Attacker's Target: " + str(attacker.target.pk))

            target.alive = True
            target.target = attacker.target
            print("Target's Target: " + str(target.target.pk))
            self.attacker.target = target
            print("Attacker's Target: " + str(attacker.target.pk))
            print("Target's Target: " + str(target.target.pk))
            self.attacker.save()
            print("Attacker's Target: " + str(attacker.target.pk))
            print("Target's Target: " + str(target.target.pk))
            target.save()
            self.valid = False
            self.save()
            # send messages
            self.game.send_message(target, REVIVED_BY_ADMIN_MESSAGE)  # TODO: clarify that attacker is the same as before?
            self.game.send_message(attacker, TARGET_REVIVED_BY_ADMIN_MESSAGE % (target, target))
        return num_reverted

    def revert(self):
        if self.from_quota_check:
            return self.quota_check.revert()
        else:
            return self.revert_helper()


class ServerState(SingletonModel):
    # NOT_LOADED = 'NOT_LOADED'
    # LOADING = 'LOADING'
    # LOADED = 'LOADED'
    # STATUS_CHOICES = (
    #     (NOT_LOADED, 'Not Loaded'),
    #     (LOADING, 'Loading'),
    #     (LOADED, 'Loaded')
    # )
    # curr_term = models.OneToOneField(Term, default=Term.get_current, null=True, blank=True, on_delete=models.SET_DEFAULT)  # TODO
    # term_status = models.CharField(max_length=255, blank=True, choices=STATUS_CHOICES, default=NOT_LOADED, editable=False)
    # subjects_status = models.CharField(max_length=255, blank=True, choices=STATUS_CHOICES, default=NOT_LOADED, editable=False)
    # courses_status = models.CharField(max_length=255, blank=True, choices=STATUS_CHOICES, default=NOT_LOADED, editable=False)

    elimination_in_progress = models.BooleanField(default=False)  # TODO
    revert_in_progress = models.BooleanField(default=False)  # TODO

    class Meta:
        verbose_name_plural = 'server state'

    def __str__(self):
        return 'Server State'