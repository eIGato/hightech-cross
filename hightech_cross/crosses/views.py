from django.http import Http404
from django.utils.timezone import now
from rest_framework import (
    permissions,
    viewsets,
)
from rest_framework.response import Response

from . import models
from .serializers import (
    CrossSerializer,
    MissionSerializer,
)


def get_current_cross(user):
    return models.Cross.objects.filter(
        users=user,
        begins_at__lte=now(),
    ).last()


class CrossViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Cross.objects.prefetch_related(
        'users',
        'missions',
    )
    serializer_class = CrossSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk, *args, **kwargs):
        if pk == 'current':
            instance = self.get_current_cross(request)
        else:
            instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def get_current_cross(self, request):
        cross = get_current_cross(request.user)
        if cross is not None:
            self.kwargs['pk'] = cross.id
        return cross


class MissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Mission.objects.prefetch_related(
        'progress_logs',
    )
    serializer_class = MissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk, cross_pk, *args, **kwargs):
        if cross_pk == 'current':
            cross_pk = self.get_current_cross(request).id
        instance = self.get_queryset().filter(
            cross_id=cross_pk,
            serial_number=pk,
        ).first()
        if instance is None:
            raise Http404
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
