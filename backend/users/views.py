from django.shortcuts import get_object_or_404

from djoser.views import UserViewSet

from drf_spectacular.utils import extend_schema, extend_schema_view

from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .serializers import CustomUserSerializer

from .models import CustomUser, Subscribe

from utils.crud import create_relation, delete_relation

from .permissions import IsAdminAuthorOrReadOnly

from events.models import Activity, Event
from events.serializers import EventSerializer


@extend_schema(tags=['Пользователи'])
@extend_schema_view(
    list=extend_schema(summary='Получение списка пользователей'),
    create=extend_schema(summary='Создание профиля пользователя'),
    retrieve=extend_schema(summary='Получение профиля пользователя'),
    update=extend_schema(summary='Изменение профиля пользователя'),
    partial_update=extend_schema(summary='Частичное изменение профиля пользователя'),
    destroy=extend_schema(summary='Удаление профиля пользователя'),
)
class CustomUserViewSet(UserViewSet):
    """Кастомный вьюсет Пользователя."""
    serializer_class = CustomUserSerializer
    queryset = CustomUser.objects.all()
    permission_classes = [permissions.IsAuthenticated,]

    def get_permissions(self):
        if self.action == 'me':
            self.permission_classes = [permissions.IsAuthenticated, ]
        elif self.request.method in ['PATCH', 'DELETE']:
            self.permission_classes = [IsAdminAuthorOrReadOnly, ]
        return super().get_permissions()

    @extend_schema(summary='Подписка')
    @action(methods=['post', 'delete'],
            detail=True,
            permission_classes=[permissions.IsAuthenticated, ])
    def subscribe(self, request, id):
        author = get_object_or_404(CustomUser, pk=id)
        if request.user != author:
            if request.method == 'POST':
                return create_relation(request,
                                       CustomUser,
                                       Subscribe,
                                       id,
                                       CustomUserSerializer,
                                       field='author')
            return delete_relation(request,
                                   CustomUser,
                                   Subscribe,
                                   id,
                                   field='author')
        return Response(
            data={'errors': 'Подписка на самого себя запрещена'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @extend_schema(summary='Все подписки')
    @action(detail=False,
            permission_classes=[permissions.IsAuthenticated, ])
    def subscriptions(self, request):
        subscribers_data = CustomUser.objects.filter(
            subscribers__user=request.user
        )
        page = self.paginate_queryset(subscribers_data)
        serializer = CustomUserSerializer(
            page, many=True, context={'request': request}
        )

        return self.get_paginated_response(serializer.data)
    
    @extend_schema(summary='Рекомендации')
    @action(methods=['GET'],
            detail=False,
            permission_classes=[permissions.IsAuthenticated, ])
    def recommendations(self, request):
        user_activity_data = Activity.objects.filter(
            users_for_activity__user=request.user
        )
        events_data = Event.objects.all()
        recommendation_events = []

        for event in events_data:
            for activity in user_activity_data.values():
                if activity in event.activity.values():
                    recommendation_events.append(event)
        serializer = EventSerializer(
            recommendation_events, many=True, context={'request': request}
        )

        return Response(serializer.data)
