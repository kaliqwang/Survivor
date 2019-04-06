from django.db import models

class GameManager(models.Manager):

    def get_current(self):
        try:
            return self.filter(has_closed=False).first()
        except self.model.DoesNotExist:
            return None

class Game(models.Model):
    # Game settings
    admin = models.ForeignKey(User, related_name='games_as_admin', blank=True, null=True, on_delete=models.SET_NULL)  # TODO: what to do if admin gets deleted? Implement some way for new admin user to take control over game
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

    @classmethod
    def get_current(cls):
        try:
            return cls.objects.filter(has_closed=False).first()
        except: cls.DoesNotExist:
            return None

    def __init__(self, *args, **kwargs):
        super(Game, self).__init__(*args, **kwargs)
        self.client = None
        if self.twilio_account_sid and self.twilio_auth_token:  # TODO: client needs to change every time twilio credentials change (e.g. in save() method)
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
        return self.players.order_by('-num_kills_copy', '-alive')  # TODO: temp fix; function name not entirely appropriate

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

    def randomize_player_sequence(self):  # TODO: this breaks elimination revert mechanism
        # TODO: for now, don't reassign player position; just randomize target assignments
        players = list(self.players_alive.order_by('?'))
        for i in range(0, len(players)):
            players[i].target = None
            players[i].save()
        last = len(players) - 1
        for i in range(0, last):
            players[i].target = players[i + 1]
            players[i].save()
        players[last].target = players[0]
        players[last].save()

        for player in players:
            message = "Player sequence has been randomized. Your new target is %s" % player.target
            if player.user.profile.phone_num:
                try:
                    self.client.messages.create(to=player.user.profile.phone_num, from_=self.twilio_phone_num, body=MESSAGE_HEADER+message)
                except Exception as e:
                    print(e)  # TODO: log error
            if player.user.email:
                send_mail(EMAIL_SUBJECT_LINE, message, EMAIL_FROM_ADDRESS, [player.user.email], fail_silently=True)

    def start(self):
        if self.num_players > 1:  # NOTE: cannot start a war with less than two players
            self.initialize_player_sequence()
            self.date_start = date.today()  # NOTE: override
            self.has_started = True
            self.details = "Game is in progress"
            self.save()
            self.send_game_start_message_all_players()
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
        self.send_message_all_players(GAME_END_MESSAGE)

    def close(self):
        self.date_close = date.today()
        self.has_closed = True
        self.save()
        if not self.has_ended:
            self.details = "Game was cancelled"
            self.save()
            self.send_message_all_players(GAME_CANCELLED_MESSAGE)

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
        # TODO: return number of players eliminated as a result of the quota check?

    def send_message(self, player, message):
        user = User.objects.select_related('profile').get(pk=player.user_id)  # single database hit
        if user.profile.phone_num:
            try:
                self.client.messages.create(to=user.profile.phone_num, from_=self.twilio_phone_num, body=MESSAGE_HEADER+message)
            except Exception as e:
                print(e)  # TODO: log error
        if user.email:
            send_mail(EMAIL_SUBJECT_LINE, message, EMAIL_FROM_ADDRESS, [user.email], fail_silently=True)

    def send_mass_message(self, players, message):
        message_list = []
        for player in players:
            user = User.objects.select_related('profile').get(pk=player.user_id)  # single database hit # TODO: bad performance; n database hits, where n is number of players
            if user.profile.phone_num:
                try:
                    self.client.messages.create(to=user.profile.phone_num, from_=self.twilio_phone_num, body=MESSAGE_HEADER+message)
                except Exception as e:
                    print(e)  # TODO: log error
            if user.email:
                send_mail(EMAIL_SUBJECT_LINE, message, EMAIL_FROM_ADDRESS, [user.email], fail_silently=True)
        #         message = (EMAIL_SUBJECT_LINE, message, EMAIL_FROM_ADDRESS, [player.user.email])
        #         message_list.append(message)
        # send_mass_mail(tuple(message_list), fail_silently=True)  # TODO: send_mail() works but send_mass_mail() doesn't; why? https://docs.djangoproject.com/en/1.11/topics/email/#django.core.mail.send_mail

    def send_game_start_message_all_players(self):
        players = Player.objects.filter(game=self).select_related('user__profile').select_related('target__user').all()  # single database hit
        for player in players:
            message = GAME_START_MESSAGE % player.target # TODO: verify that player.target.__str__() does not result in extra database hit to get player.target.user.first_name and player.target.user.last_name
            if player.user.profile.phone_num:
                try:
                    self.client.messages.create(to=player.user.profile.phone_num, from_=self.twilio_phone_num, body=MESSAGE_HEADER+message)
                except Exception as e:
                    print(e)  # TODO: log error
            if player.user.email:
                send_mail(EMAIL_SUBJECT_LINE, message, EMAIL_FROM_ADDRESS, [player.user.email], fail_silently=True)

    def send_new_target_message_all_players_alive(self):
        players = Player.objects.filter(game=self).filter(alive=True).select_related('user__profile').select_related('target__user').all()  # single database hit
        for player in players:
            message = GAME_START_MESSAGE % player.target # TODO: verify that player.target.__str__() does not result in extra database hit to get player.target.user.first_name and player.target.user.last_name
            if player.user.profile.phone_num:
                try:
                    self.client.messages.create(to=player.user.profile.phone_num, from_=self.twilio_phone_num, body=MESSAGE_HEADER+message)
                except Exception as e:
                    print(e)  # TODO: log error
            if player.user.email:
                send_mail(EMAIL_SUBJECT_LINE, message, EMAIL_FROM_ADDRESS, [player.user.email], fail_silently=True)

    def send_message_to_admin(self, message):  # TODO: temp
        send_mail(EMAIL_SUBJECT_LINE, message, EMAIL_FROM_ADDRESS, [self.admin.email], fail_silently=True)
