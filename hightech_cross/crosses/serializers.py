from rest_framework import serializers

from . import models


class ShortMissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Mission
        fields = [
            'serial_number',
            'name',
            'description',
            'lattitude',
            'longitude',
        ]


class CrossSerializer(serializers.ModelSerializer):
    users = serializers.ListField(source='user_table')
    missions = ShortMissionSerializer(many=True, required=False)

    class Meta:
        model = models.Cross
        fields = [
            'name',
            'begins_at',
            'ends_at',
            'users',
            'missions',
        ]
