"""Serializers and helpers for `crosses` app views."""
from decimal import Decimal

from django.db.models import QuerySet
from django.utils.duration import duration_string
from rest_framework import serializers

from . import models


class CoordinateField(serializers.Field):
    """Field for latitude or longitude."""

    def to_representation(self, value: Decimal) -> str:
        """Format `value` like `15°16'17"`."""
        degrees = int(value)
        minutes = (value % 1) * 60
        seconds = (minutes % 1) * 60
        return f'{degrees}\xb0{int(minutes)}\'{int(seconds)}"'


class AnswerListSerializer(serializers.ListSerializer):
    """Filter only answers from logs."""

    def to_representation(self, data: QuerySet) -> list:
        data = data.filter(event__in=(
            models.ProgressEvent.RIGHT_ANSWER,
            models.ProgressEvent.WRONG_ANSWER,
        ))
        return super().to_representation(data)


class AnswerSerializer(serializers.ModelSerializer):
    text = serializers.CharField(source='details.text')

    class Meta:
        model = models.ProgressLog
        list_serializer_class = AnswerListSerializer
        fields = [
            'created_at',
            'is_right',
            'text',
        ]


class PromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Prompt
        fields = [
            'sn',
            'text',
        ]
        read_only_fields = [
            'sn',
            'text',
        ]

    def to_representation(self, instance: models.Prompt) -> dict:
        representation = super().to_representation(instance)
        if not models.ProgressLog.objects.filter(
            user_id=self.context['request'].user.id,
            event=models.ProgressEvent.GET_PROMPT,
            details__sn=instance.sn,
        ).exists():
            representation['text'] = None
        return representation


class MissionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, source='progress_logs')
    prompts = PromptSerializer(many=True)
    lat = CoordinateField()
    lon = CoordinateField()
    finished = serializers.SerializerMethodField('get_finished')
    penalty = serializers.SerializerMethodField('get_penalty')

    class Meta:
        model = models.Mission
        fields = [
            'sn',
            'name',
            'description',
            'lat',
            'lon',
            'answers',
            'prompts',
            'finished',
            'penalty',
        ]

    def get_finished(self, instance: models.Mission) -> bool:
        return instance.get_finished(
            user_id=self.context['request'].user.id,
        )

    def get_penalty(self, instance: models.Mission) -> str:
        return duration_string(instance.get_penalty(
            user_id=self.context['request'].user.id,
        ))


class LeaderMissionSerializer(serializers.Serializer):
    sn = serializers.IntegerField()
    finished = serializers.BooleanField()


class LeaderSerializer(serializers.Serializer):
    name = serializers.CharField()
    missions = LeaderMissionSerializer(many=True)
    missions_finished = serializers.IntegerField()
    penalty = serializers.DurationField()


class CrossSerializer(serializers.ModelSerializer):
    leaderboard = LeaderSerializer(many=True)

    class Meta:
        model = models.Cross
        fields = [
            'id',
            'name',
            'begins_at',
            'ends_at',
            'leaderboard',
        ]
