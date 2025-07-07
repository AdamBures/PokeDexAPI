from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('pokemon/<str:name>/', views.pokemon_detail, name='pokemon_detail'),
    path('compare/', views.compare_pokemons, name='compare'),
    path('search/', views.search, name='search'),
    path('arena/', views.arena, name='arena'),
    path('battles/', views.battle_history, name='battle_history_list'),
]