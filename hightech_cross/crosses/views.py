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
        'missions__progress_logs',
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
        return Response(serializer.data)
