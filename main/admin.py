from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import *


class UserProfileInlineAdmin(admin.StackedInline):
    model = UserProfile

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInlineAdmin,)


class GameAdmin(admin.ModelAdmin):
    # list_display = ('name', 'code', 'term', 'courses_total_count', 'is_active', 'courses_loaded')
    # list_select_related = ('term',)
    # list_filter = ('term', 'courses_loaded')
    # search_fields = ('name', 'code', 'term__name')
    # fields = ('name', 'code', 'term', 'is_active', 'courses_loaded')
    # readonly_fields = ('name', 'code', 'term', 'is_active')
    # filter_horizontal = ('members',)
    # inlines = (MeetingTimeInlineAdmin,)
    pass


class PlayerAdmin(admin.ModelAdmin):

    actions = ['eliminate_targets']

    def eliminate_targets(self, request, queryset):
        for player in queryset:  # TODO: queryset.all()?
            player.eliminate_target()
        num_selected = queryset.count()
        if num_selected == 1:
            message_bit = "1 target was"
        else:
            message_bit = "%s targets were" % num_selected
        self.message_user(request, "%s successfully eliminated." % message_bit)
    eliminate_targets.short_description = "Eliminate targets for selected players"


class QuotaCheckAdmin(admin.ModelAdmin):

    actions = ['revert']

    def revert(self, request, queryset):
        num_reverted = 0
        for quota_check in queryset:  # TODO: queryset.all()?
            num_reverted += quota_check.revert()
        if num_reverted == 1:
            message_bit = "1 quota check was"
        else:
            message_bit = "%s quota checks were" % num_reverted
        self.message_user(request, "%s successfully reverted." % message_bit)

    revert.short_description = "Revert selected quota checks"


class EliminationAdmin(admin.ModelAdmin):

    actions = ['revert']

    def revert(self, request, queryset):
        num_reverted = 0
        for elimination in queryset:  # TODO: queryset.all()?
            num_reverted += elimination.revert()
        if num_reverted == 1:
            message_bit = "1 elimination was"
        else:
            message_bit = "%s eliminations were" % num_reverted
        self.message_user(request, "%s successfully reverted." % message_bit)
    revert.short_description = "Revert selected eliminations"



admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(QuotaCheck, QuotaCheckAdmin)
admin.site.register(Elimination, EliminationAdmin)
