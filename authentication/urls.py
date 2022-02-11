from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterAPIView.as_view(), name='auth_register'),
    path('login/', views.LoginAPIView.as_view(), name='auth_login'),
    path('verify-email/', views.VerifyEmailAPIView.as_view(), name='auth_verify_email'),
    path('reset-password-request/', views.ResetPasswordRequestAPIView.as_view(), name='auth_reset_password_request'),
    path('reset-password/<uidb64>/<token>/', views.ResetPasswordTokenCheckAPIView.as_view(),
         name='auth_reset_password_confirm'),
    path('reset-password-complete/', views.ResetPasswordAPIView.as_view(), name='auth_reset_password'),
    path('tokens/refresh/', views.TokenRefreshAPIView.as_view(), name='auth_token_refresh'),
    path('profile/upload-url/', views.GenerateProfileUrl.as_view(), name='auth_profile_upload_url'),
    path('profile/create/', views.CreateProfileAPIView.as_view(), name='auth_profile_create'),
    path('profile/current/', views.CurrentProfileAPIView.as_view(), name='auth_profile_current'),
    path('user/list/', views.UsersListAPIView.as_view(), name='auth_user_list'),
    path('user/detail/<uid>/', views.UserDetailAPIView.as_view(), name='auth_user_detail'),
]
