from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (Vehicle, City, UserCoeff, Calculation, MapRoute, SavedRoute, Trip,
                     UserBook, BookState, UserNote, UserLibrary)

# --- Розширений перегляд користувачів ---
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'first_name', 'email', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'email')

try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, CustomUserAdmin)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('name', 'plate', 'user', 'category')
    list_filter = ('category', 'user')
    search_fields = ('name', 'plate', 'user__username')


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'percent', 'user')
    search_fields = ('name',)


@admin.register(UserCoeff)
class UserCoeffAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'type', 'user')
    list_filter = ('type', 'user')
    search_fields = ('name', 'user__username')


@admin.register(MapRoute)
class MapRouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'distance', 'user', 'created_at')
    list_filter = ('user', 'created_at')
    search_fields = ('name', 'user__username')
    exclude = ('image_data',)


@admin.register(SavedRoute)
class SavedRouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'distance', 'max_weight', 'user', 'created_at')
    list_filter = ('user', 'created_at')
    search_fields = ('name', 'user__username')


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('name', 'car', 'distance', 'fuel_consumed', 'user', 'created_at')
    list_filter = ('user', 'created_at')
    search_fields = ('name', 'user__username')


@admin.register(Calculation)
class CalculationAdmin(admin.ModelAdmin):
    """Старий архів (до розділення таблиць): лише для перегляду, нові записи сюди не пишуться."""
    list_display = ('route', 'kind', 'distance', 'fuel_consumed', 'user', 'created_at')
    list_filter = ('kind', 'user', 'created_at')
    exclude = ('image_data',)


@admin.register(UserBook)
class UserBookAdmin(admin.ModelAdmin):
    list_display = ('title', 'car_title', 'user', 'created_at')
    list_filter = ('user', 'created_at')


@admin.register(UserNote)
class UserNoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'updated_at')


@admin.register(UserLibrary)
class UserLibraryAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'user', 'uploaded_at')


@admin.register(BookState)
class BookStateAdmin(admin.ModelAdmin):
    list_display = ('user', 'car_title', 'updated_at')