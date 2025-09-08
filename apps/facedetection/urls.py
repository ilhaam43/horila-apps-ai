from django.urls import path

from .views import *

urlpatterns = [
    path("config/", FaceDetectionConfigAPIView.as_view(), name="face-detection-config-api"),
    path("setup/", EmployeeFaceDetectionGetPostAPIView.as_view(), name="employee-face-detection-api"),
    path("", face_detection_config, name="face-config"),
]
