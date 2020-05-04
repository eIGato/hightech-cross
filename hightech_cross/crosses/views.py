from django.utils.timezone import now
from rest_framework import (
    permissions,
    viewsets,
)
from rest_framework.response import Response

from . import models
from .serializers import (
    CrossSerializer,
)


class CrossViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Cross.objects.prefetch_related(
        'users',
        'missions',
    )
    serializer_class = CrossSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        slug = request.path.split('/')[-2]
        if slug == 'current':
            current_time = now()
            instance = self.get_queryset().filter(
                users=request.user,
                begins_at__lte=current_time,
            ).last()
        else:
            instance = self.get_object()
        serializer = self.get_serializer(instance)
        for mission in serializer.data['missions']:
            mission['status'] = instance.missions.get(
                id=mission['id'],
            ).get_status(user_id=request.user.id)
        return Response(serializer.data)
