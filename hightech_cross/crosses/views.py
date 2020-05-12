"""Views and viewsets for `crosses` app."""
import uuid

from django.http import Http404
from django.utils.timezone import now
from rest_framework import (
    permissions,
    status,
    viewsets,
)
from rest_framework.request import Request
from rest_framework.response import Response

from . import models
from .serializers import (
    AnswerSerializer,
    CrossSerializer,
    MissionSerializer,
    PromptSerializer,
)


def get_mission(cross_id: uuid.UUID, sn: int) -> models.Mission:
    """Shortcut to get mission by given args."""
    mission = models.Mission.objects.filter(
        cross_id=cross_id,
        sn=sn,
    ).first()
    if mission is None:
        raise Http404
    return mission


class CurrentCrossMixin:
    def get_current_cross(self, user_id: uuid.UUID) -> models.Cross:
        """Get last of crosses ever started for user."""
        cross = models.Cross.objects.filter(
            users=user_id,
            begins_at__lte=now(),
        ).last()
        if cross is None:
            raise Http404
        if 'cross_pk' in self.kwargs:
            self.kwargs['cross_pk'] = cross.id
        else:
            self.kwargs['pk'] = cross.id
        return cross


class CrossViewSet(CurrentCrossMixin, viewsets.ReadOnlyModelViewSet):
    queryset = models.Cross.objects.prefetch_related(
        'users',
        'missions',
    )
    serializer_class = CrossSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(
        self,
        request: Request,
        pk: str,
        *args,
        **kwargs,
    ) -> Response:
        if pk == 'current':
            instance = self.get_current_cross(request.user.id)
        else:
            instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class MissionViewSet(CurrentCrossMixin, viewsets.ReadOnlyModelViewSet):
    queryset = models.Mission.objects.filter(
        cross__begins_at__lt=now(),
    ).prefetch_related(
        'progress_logs',
    )
    serializer_class = MissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(
        self,
        request: Request,
        pk: str,
        cross_pk: str,
        *args,
        **kwargs,
    ) -> Response:
        if cross_pk == 'current':
            cross_pk = self.get_current_cross(request.user.id).id
        instance = get_mission(
            cross_id=cross_pk,
            sn=pk,
        )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def list(
        self,
        request: Request,
        cross_pk: str,
        *args,
        **kwargs,
    ) -> Response:
        if cross_pk == 'current':
            cross_pk = self.get_current_cross(request.user.id).id
        missions = self.get_queryset().filter(cross_id=cross_pk)
        serializer = self.get_serializer(missions, many=True)
        return Response(serializer.data)


class AnswerViewSet(
    CurrentCrossMixin,
    viewsets.mixins.CreateModelMixin,
    viewsets.mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = models.ProgressLog.objects.filter(event__in=(
        models.ProgressEvent.RIGHT_ANSWER,
        models.ProgressEvent.WRONG_ANSWER,
    ))
    serializer_class = AnswerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(
        self,
        request: Request,
        cross_pk: str,
        mission_pk: str,
        *args,
        **kwargs,
    ) -> Response:
        if cross_pk == 'current':
            cross_pk = self.get_current_cross(request.user.id).id
        mission = get_mission(
            cross_id=cross_pk,
            sn=mission_pk,
        )
        return Response(
            mission.give_answer(
                user_id=request.user.id,
                text=request.data['text'],
            ),
            status=status.HTTP_201_CREATED,
        )


class PromptViewSet(
    CurrentCrossMixin,
    viewsets.mixins.UpdateModelMixin,
    viewsets.mixins.ListModelMixin,
    viewsets.mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = models.Prompt.objects.all()
    serializer_class = PromptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(
        self,
        request: Request,
        pk: str,
        cross_pk: str,
        mission_pk: str,
        *args,
        **kwargs,
    ) -> Response:
        if cross_pk == 'current':
            cross_pk = self.get_current_cross(request.user.id).id
        mission = get_mission(
            cross_id=cross_pk,
            sn=mission_pk,
        )
        prompt = mission.get_prompt(
            user_id=request.user.id,
            sn=pk,
        )
        if prompt is None:
            raise Http404
        serializer = self.get_serializer(prompt)
        return Response(serializer.data)

    def retrieve(
        self,
        request: Request,
        pk: str,
        cross_pk: str,
        mission_pk: str,
        *args,
        **kwargs,
    ) -> Response:
        if cross_pk == 'current':
            cross_pk = self.get_current_cross(request.user.id).id
        mission = get_mission(
            cross_id=cross_pk,
            sn=mission_pk,
        )
        instance = mission.prompts.filter(sn=pk).first()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def list(
        self,
        request: Request,
        cross_pk: str,
        mission_pk: str,
        *args,
        **kwargs,
    ) -> Response:
        if cross_pk == 'current':
            cross_pk = self.get_current_cross(request.user.id).id
        return super().list(request, cross_pk, mission_pk, *args, **kwargs)
