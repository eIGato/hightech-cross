from rest_framework import serializers

from . import models


class AnswerSerializer(serializers.ModelSerializer):
    text = serializers.CharField(source='details.text')

    class Meta:
        model = models.ProgressLog
        fields = [
            'created_at',
            'is_right',
            'text',
        ]


class MissionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, source='progress_logs')

    class Meta:
        model = models.Mission
        fields = [
            'serial_number',
            'name',
            'description',
            'lattitude',
            'longitude',
            'answers',
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.update(instance.get_status(
            user_id=self.context['request'].user.id,
        ))
        return representation


class CrossSerializer(serializers.ModelSerializer):
    users = serializers.ListField(source='user_table')

    class Meta:
        model = models.Cross
        fields = [
            'id',
            'name',
            'begins_at',
            'ends_at',
            'users',
        ]
