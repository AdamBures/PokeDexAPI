from django.contrib import admin

# Register your models here.
from .models import PokemonType, Pokemon, Evolution, BattleHistory

admin.site.register(PokemonType)
admin.site.register(Pokemon)
admin.site.register(Evolution)
admin.site.register(BattleHistory)

