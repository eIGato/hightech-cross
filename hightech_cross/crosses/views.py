from django.http import Http404
from django.utils.timezone import now
from rest_framework import (
    permissions,
    viewsets,
)
from rest_framework.response import Response

from . import models
from .serializers import (
    AnswerSerializer,
    CrossSerializer,
    MissionSerializer,
)


def get_current_cross(user_id):
    cross = models.Cross.objects.filter(
        users=user_id,
        begins_at__lte=now(),
    ).last()
    if cross is None:
        raise Http404
    return cross


def get_mission(cross_id, serial_number):
    mission = models.Mission.objects.filter(
        cross_id=cross_id,
        serial_number=serial_number,
    ).first()
    if mission is None:
        raise Http404
    return mission


class CrossViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Cross.objects.prefetch_related(
        'users',
        'missions',
    )
    serializer_class = CrossSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk, *args, **kwargs):
        if pk == 'current':
            instance = get_current_cross(request.user.id)
        else:
            instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class MissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Mission.objects.prefetch_related(
        'progress_logs',
    )
    serializer_class = MissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk, cross_pk, *args, **kwargs):
        if cross_pk == 'current':
            cross_pk = get_current_cross(request.user.id).id
        instance = get_mission(
            cross_id=cross_pk,
            serial_number=pk,
        )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def list(self, request, cross_pk, *args, **kwargs):
        if cross_pk == 'current':
            cross_pk = self.get_current_cross(request).id
        missions = self.get_queryset().filter(cross_id=cross_pk)
        serializer = self.get_serializer(missions, many=True)
        return Response(serializer.data)

    def get_current_cross(self, request):
        cross = get_current_cross(request.user)
        if cross is None:
            raise Http404
        self.kwargs['cross_pk'] = cross.id
        return cross


class AnswerViewSet(
    viewsets.mixins.CreateModelMixin,
    viewsets.mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = models.ProgressLog.objects.filter(event__in=(
        models.event_choices['RIGHT_ANSWER'],
        models.event_choices['WRONG_ANSWER'],
    ))
    serializer_class = AnswerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, cross_pk, mission_pk, *args, **kwargs):
        if cross_pk == 'current':
            cross_pk = get_current_cross(request.user.id).id
        mission = get_mission(
            cross_id=cross_pk,
            serial_number=mission_pk,
        )
        return Response(mission.give_answer(
            user_id=request.user.id,
            text=request.data['text'],
        ))

    def get_current_cross(self, request):
        cross = get_current_cross(request.user.id)
        if cross is None:
            raise Http404
        self.kwargs['cross_pk'] = cross.id
        return cross
