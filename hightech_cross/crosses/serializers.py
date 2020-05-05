from rest_framework import serializers

from . import models


class MissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Mission
        fields = [
            'serial_number',
            'name',
            'description',
            'lattitude',
            'longitude',
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
