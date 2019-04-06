from django.db import models

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
        user = self.user # TODO: bad performance; use select_related('user')
        return user.first_name + " " + user.last_name

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
