from django.db import models

class QuotaCheck(models.Model):
    game = models.ForeignKey(Game, related_name='quota_checks', default=Game.get_current, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    valid = models.BooleanField(default=True)

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
