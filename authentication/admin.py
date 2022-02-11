from django.contrib import admin
from .models import Profile, User, Media

admin.site.register(User)
admin.site.register(Profile)
admin.site.register(Media)
