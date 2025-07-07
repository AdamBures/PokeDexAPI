# models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import requests


class PokemonType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#000000')  # Hex barva
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Pokémon typ"
        verbose_name_plural = "Pokémon typy"


class Pokemon(models.Model):
    name = models.CharField(max_length=100, unique=True)
    pokedex_id = models.PositiveIntegerField(unique=True)
    height = models.PositiveIntegerField(help_text="Výška v decimetrech")
    weight = models.PositiveIntegerField(help_text="Váha v hectogramech")
    base_experience = models.PositiveIntegerField(default=0)
    sprite_url = models.URLField(blank=True, null=True)
    types = models.ManyToManyField(PokemonType, related_name='pokemon')
    abilities = models.ManyToManyField('Ability', related_name='pokemon', blank=True)

    # Základní statistiky
    hp = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(255)])
    attack = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(255)])
    defense = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(255)])
    special_attack = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(255)])
    special_defense = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(255)])
    speed = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(255)])
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_legendary = models.BooleanField(default=False)
    is_mythical = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name} (#{self.pokedex_id})"
    
    @property
    def total_stats(self):
        return self.hp + self.attack + self.defense + self.special_attack + self.special_defense + self.speed
    
    @property
    def type_names(self):
        return [t.name for t in self.types.all()]
    
    def get_stats_dict(self):
        """Vrací statistiky ve formátu kompatibilním s původním API"""
        return {
            'hp': self.hp,
            'attack': self.attack,
            'defense': self.defense,
            'special-attack': self.special_attack,
            'special-defense': self.special_defense,
            'speed': self.speed
        }
    
    class Meta:
        verbose_name = "Pokémon"
        verbose_name_plural = "Pokémoni"
        ordering = ['pokedex_id']


class Ability(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Schopnost"
        verbose_name_plural = "Schopnosti"


class Evolution(models.Model):
    from_pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE, related_name='evolves_to')
    to_pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE, related_name='evolves_from')
    level = models.PositiveIntegerField(null=True, blank=True)
    item = models.CharField(max_length=100, blank=True)
    condition = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return f"{self.from_pokemon.name} -> {self.to_pokemon.name}"
    
    class Meta:
        verbose_name = "Evoluce"
        verbose_name_plural = "Evoluce"
        unique_together = ['from_pokemon', 'to_pokemon']


class BattleHistory(models.Model):
    BATTLE_RESULT_CHOICES = [
        ('win', 'Výhra'),
        ('lose', 'Prohra'),
        ('draw', 'Remíza'),
    ]
    
    user_team = models.ManyToManyField(Pokemon, related_name='user_battles')
    cpu_team = models.ManyToManyField(Pokemon, related_name='cpu_battles')
    result = models.CharField(max_length=10, choices=BATTLE_RESULT_CHOICES)
    battle_log = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Bitva {self.created_at.strftime('%d.%m.%Y %H:%M')} - {self.get_result_display()}"
    
    class Meta:
        verbose_name = "Historie bitvy"
        verbose_name_plural = "Historie bitev"
        ordering = ['-created_at']
