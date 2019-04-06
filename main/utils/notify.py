from django.core.mail import send_mass_mail, send_mail
from twilio.rest import Client

GAME_START_MESSAGE = "The game has started! Your target is %s. Stay safe, have fun, and good luck!"  # TODO: display initial target name
GAME_END_MESSAGE = "The game has ended. See the website for more info."
GAME_CANCELLED_MESSAGE = "The game has been cancelled by an admin. Please check the website for more details."

EMAIL_SUBJECT_LINE = 'FIJI Survivor'
EMAIL_FROM_ADDRESS = 'fijisurvivor@gmail.com'
MESSAGE_HEADER = '---- FIJI Survivor ----\n' # TODO

ELIMINATED_BY_QUOTA_CHECK_MESSAGE = "You have been eliminated by for not meeting the quota."
TARGET_ELIMINATED_BY_QUOTA_CHECK_MESSAGE = "Your target has been eliminated for not meeting the quota. Your new target is %s."

ELIMINATED_BY_ATTACKER_MESSAGE = "You have been eliminated by %s."
TARGET_ELIMINATED_BY_ATTACKER_MESSAGE = "Congratulations on eliminating %s. Your new target is %s."

ELIMINATED_BY_TARGET_MESSAGE = "You have been eliminated by your target %s in self defense."
TARGET_ELIMINATED_BY_TARGET_MESSAGE = "Your target (%s) has been eliminated by their target in self defense. Your new target is %s"
ATTACKER_ELIMINATED_BY_TARGET_MESSAGE = "Congratulations on eliminating %s in self defense."

REVIVED_BY_ADMIN_MESSAGE = "You have been revived by an admin."
TARGET_REVIVED_BY_ADMIN_MESSAGE = "Your elimination of %s was reverted by an admin. Your new target is %s."

class NotificationService:

    def __init__(self, twilio_account_sid, twilio_auth_token, twilio_phone_num):
        self.twilio_phone_num = twilio_phone_num
        self.client = Client(twilio_account_sid, twilio_auth_token)

    def send_message(self, user, message):
        try:
            if user.profile.phone_num:
                self.client.messages.create(
                    to = user.profile.phone_num,
                    from_ = self.twilio_phone_num,
                    body = MESSAGE_HEADER + message
                )
            if user.email:
                send_mail(
                    EMAIL_SUBJECT_LINE,
                    message,
                    EMAIL_FROM_ADDRESS,
                    [user.email],
                    fail_silently = True
                )
        except Exception as e:
            print(e)  # TODO: log error



    # def send_message(self, player, message):
    #     user = User.objects.select_related('profile').get(pk=player.user_id)  # single database hit
    #     if user.profile.phone_num:
    #         try:
    #             self.client.messages.create(to=user.profile.phone_num, from_=self.twilio_phone_num, body=MESSAGE_HEADER+message)
    #         except Exception as e:
    #             print(e)  # TODO: log error
    #     if user.email:
    #         send_mail(EMAIL_SUBJECT_LINE, message, EMAIL_FROM_ADDRESS, [user.email], fail_silently=True)

    # def send_mass_message(self, players, message):
    #     message_list = []
    #     for player in players:
    #         user = User.objects.select_related('profile').get(pk=player.user_id)  # single database hit # TODO: bad performance; n database hits, where n is number of players
    #         if user.profile.phone_num:
    #             try:
    #                 self.client.messages.create(to=user.profile.phone_num, from_=self.twilio_phone_num, body=MESSAGE_HEADER+message)
    #             except Exception as e:
    #                 print(e)  # TODO: log error
    #         if user.email:
    #             send_mail(EMAIL_SUBJECT_LINE, message, EMAIL_FROM_ADDRESS, [user.email], fail_silently=True)
    #     #         message = (EMAIL_SUBJECT_LINE, message, EMAIL_FROM_ADDRESS, [player.user.email])
    #     #         message_list.append(message)
    #     # send_mass_mail(tuple(message_list), fail_silently=True)  # TODO: send_mail() works but send_mass_mail() doesn't; why? https://docs.djangoproject.com/en/1.11/topics/email/#django.core.mail.send_mail

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
