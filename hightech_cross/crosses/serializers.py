from rest_framework import serializers

from . import models


class AnswerListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
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
            'serial_number',
            'text',
        ]
        read_only_fields = [
            'serial_number',
            'text',
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if not models.ProgressLog.objects.filter(
            user_id=self.context['request'].user.id,
            event=models.ProgressEvent.GET_PROMPT,
            details__serial_number=instance.serial_number,
        ).exists():
            representation['text'] = None
        return representation


class MissionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, source='progress_logs')
    prompts = PromptSerializer(many=True)

    class Meta:
        model = models.Mission
        fields = [
            'serial_number',
            'name',
            'description',
            'lattitude',
            'longitude',
            'answers',
            'prompts',
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
