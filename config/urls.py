from django.contrib import admin
from django.urls import path
from main_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index_view, name='index'),
    path('logout/', views.logout_view, name='logout'),

    path('calc/', views.calc_view, name='calc'),
    path('cars/', views.cars_view, name='cars'),
    path('cities/', views.cities_view, name='cities'),
    path('coeffs/', views.coeffs_view, name='coeffs'),
    path('book/', views.book_view, name='book'),
    path('library/', views.library_view, name='library'),
    path('map/', views.map_view, name='map'),
    path('preview/', views.preview_view, name='preview'),

    # API маршрути для AJAX
    path('api/cars/', views.cars_api, name='cars_api'),
    path('api/cities/', views.cities_api, name='cities_api'),
    path('api/coeffs/', views.coeffs_api, name='coeffs_api'),
    path('api/book/', views.book_api, name='book_api'),
    path('api/map/', views.map_api, name='map_api'),
    path('api/library/', views.library_api, name='library_api'),
]