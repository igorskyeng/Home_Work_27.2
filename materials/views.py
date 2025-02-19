from django.shortcuts import get_object_or_404

from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from materials.models import Course, Lesson, Subscription
from materials.paginators import LessonPaginator
from materials.permissions import IsModerator, IsOwner
from materials.serliazers import CourseSerializers, LessonSerializers, SubscriptionSerializer
from materials.tasks import send_email


class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializers

    def perform_create(self, serializer):
        new_course = serializer.save()
        new_course.owner = self.request.user
        new_course.save()

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [IsAuthenticated & ~IsModerator]

        elif self.action in ['retrieve', 'update', 'list']:
            self.permission_classes = [IsAuthenticated & (IsModerator | IsOwner)]

        elif self.action == 'destroy':
            self.permission_classes = [IsAuthenticated & IsOwner]

        return super().get_permissions()

    def get_queryset(self):
        if not self.request.user.is_staff:
            return Course.objects.filter(owner=self.request.user)

        elif self.request.user.is_staff:
            return Course.objects.all()

    def update(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        send_email.delay(course_id=course.id)

        return super().update(request)


class LessonCreateAPIView(generics.CreateAPIView):
    serializer_class = LessonSerializers
    queryset = Lesson.objects.all()
    permission_classes = [IsAuthenticated & ~IsModerator]

    def perform_create(self, serializer):
        new_lesson = serializer.save()
        new_lesson.owner = self.request.user
        new_lesson.save()


class LessonListAPIView(generics.ListAPIView):
    serializer_class = LessonSerializers
    permission_classes = [IsAuthenticated & (IsModerator | IsOwner)]
    pagination_class = LessonPaginator

    def get_queryset(self):
        if not self.request.user.is_staff:
            return Lesson.objects.filter(owner=self.request.user)

        elif self.request.user.is_staff:
            return Lesson.objects.all()


class LessonRetrieveAPIView(generics.RetrieveAPIView):
    serializer_class = LessonSerializers
    permission_classes = [IsAuthenticated & (IsModerator | IsOwner)]

    def get_queryset(self):
        if not self.request.user.is_staff:
            return Course.objects.filter(owner=self.request.user)

        elif self.request.user.is_staff:
            return Course.objects.all()


class LessonUpdateAPIView(generics.UpdateAPIView):
    serializer_class = LessonSerializers
    permission_classes = [IsAuthenticated & (IsModerator | IsOwner)]

    def get_queryset(self):
        if not self.request.user.is_staff:
            return Course.objects.filter(owner=self.request.user)

        elif self.request.user.is_staff:
            return Course.objects.all()


class LessonDestroyAPIView(generics.DestroyAPIView):
    serializer_class = LessonSerializers
    permission_classes = [IsAuthenticated & IsOwner]

    def get_queryset(self):
        if not self.request.user.is_staff:
            return Course.objects.filter(owner=self.request.user)

        elif self.request.user.is_staff:
            return Course.objects.all()


class SubscriptionAPIView(APIView):
    serializer_class = SubscriptionSerializer

    def post(self, *args, **kwargs):
        user = self.request.user
        course_id = self.request.data.get('course')
        course = get_object_or_404(Course, pk=course_id)
        subs_item = Subscription.objects.all().filter(user=user).filter(course=course)

        if subs_item.exists():
            subs_item.delete()
            message = 'Подписка отключена'

        else:
            Subscription.objects.create(user=user, course=course)
            message = 'Подписка включена'

        return Response({"message": message})
