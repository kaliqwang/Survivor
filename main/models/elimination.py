from django.db import models

class Elimination(models.Model):
    game = models.ForeignKey(Game, related_name='eliminations', default=Game.get_current, on_delete=models.CASCADE)  # TODO: redundant; players already store game information
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
        return self.quota_check_id is not None  # TODO: is id of null foreign key None or 0?

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
            # target = self.target
            # attacker = target.attacker  # database hit
            # target_target = target.target  # database hit
            # attacker.target = target_target
            # target.target = None
            # target.alive = False
            # target.save()
            # attacker.save()
            # self.attacker = attacker

            self.attacker = self.target.attacker  # single database hit
            self.attacker.target = self.target.target  # single database hit
            self.target.target = None
            self.target.alive = False
            self.target.save()
            self.attacker.save()
            if self.from_quota_check:  # killed by quota check
                self.game.send_message(self.target, ELIMINATED_BY_QUOTA_CHECK_MESSAGE)  # single database hit
                self.game.send_message(self.attacker, TARGET_ELIMINATED_BY_QUOTA_CHECK_MESSAGE % self.attacker.target)  # single database hit
            elif self.is_reverse:  # self-defense kill
                self.game.send_message(self.target, ELIMINATED_BY_TARGET_MESSAGE % self.attacker.target)  # single database hit
                self.game.send_message(self.attacker, TARGET_ELIMINATED_BY_TARGET_MESSAGE % (self.target, self.attacker.target))  # single database hit
                self.game.send_message(self.attacker.target, ATTACKER_ELIMINATED_BY_TARGET_MESSAGE % self.target)  # single database hit
            else:  # normal kill
                self.game.send_message(self.target, ELIMINATED_BY_ATTACKER_MESSAGE % self.attacker)  # single database hit
                self.game.send_message(self.attacker, TARGET_ELIMINATED_BY_ATTACKER_MESSAGE % (self.target, self.attacker.target))  # single database hit
            self.game.do_check_end()
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
