from django.contrib import admin

from apps.test_generation.models import TestCase


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "source_url", "created_at")
