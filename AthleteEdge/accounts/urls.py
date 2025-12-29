from django.urls import path
from accounts.views import DetectAPIView, DetectVideoAPIView, SignUpView,LoginView, ForgetPasswordView, CreateListAthlete, AthleteAttendence, TrainingVideoUploadAPIView,PredictFromVideo, ForgetPasswordView, GetAthleteAPIView
urlpatterns = [
    path('sign-up/', SignUpView.as_view(), name="signup"),
    path('login/', LoginView.as_view(), name='login'),
    path('forget-password/', ForgetPasswordView.as_view(), name='forget-password'),
    path('create-athlete/', CreateListAthlete.as_view(), name='create-athlete'),
    path('athlete-attendence/', AthleteAttendence.as_view(), name='athlete-attendence'),
    path("upload-video/", TrainingVideoUploadAPIView.as_view(), name="upload-video"),
    path("predict-from-video/", PredictFromVideo.as_view(), name='predict-from-video'),
    path("forgot-password/", ForgetPasswordView.as_view(), name="forgot-password"),
    path("get-athlete/", GetAthleteAPIView.as_view(), name="get-athlete"),
    # path('detect/', DetectAPIView.as_view(), name='detect'),
    path('detect/', DetectVideoAPIView.as_view(), name='detect'),
]