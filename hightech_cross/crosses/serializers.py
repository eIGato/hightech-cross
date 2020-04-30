from django.contrib.auth.models import User
from rest_framework import serializers

from . import models


class ShortUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'username',
        ]


class ShortMissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Mission
        fields = [
            'id',
            'name',
            'description',
            'lattitude',
            'longitude',
        ]


class CrossSerializer(serializers.ModelSerializer):
    users = ShortUserSerializer(many=True, required=False)
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
