from django.contrib import admin

from . import models


@admin.register(models.Cross)
class CrossAdmin(admin.ModelAdmin):
    pass


@admin.register(models.Mission)
class MissionAdmin(admin.ModelAdmin):
    pass


@admin.register(models.Prompt)
class PromptAdmin(admin.ModelAdmin):
    pass


@admin.register(models.ProgressLog)
class ProgressLogAdmin(admin.ModelAdmin):
    pass
