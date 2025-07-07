# services.py
import requests
from django.core.cache import cache
from django.db import transaction
from .models import Pokemon, PokemonType, Evolution, BattleHistory
from typing import List, Dict, Optional


def get_pokemon_from_db(name_or_id) -> Optional[Pokemon]:
    """Získá Pokémona z databáze podle jména nebo ID"""
    try:
        if str(name_or_id).isdigit():
            return Pokemon.objects.select_related().prefetch_related('types').get(pokedex_id=int(name_or_id))
        else:
            return Pokemon.objects.select_related().prefetch_related('types').get(name__iexact=name_or_id)
    except Pokemon.DoesNotExist:
        return None


def get_pokemon(name_or_id, use_cache=True) -> Optional[Dict]:
    """
    Získá Pokémona - nejdřív z DB, pak z API
    Vrací data v původním formátu pro kompatibilitu
    """
    # Pokus o načtení z databáze
    pokemon_db = get_pokemon_from_db(name_or_id)
    if pokemon_db:
        return convert_db_to_api_format(pokemon_db)
    
    # Pokud není v DB, načti z API
    cache_key = f"pokemon_{str(name_or_id).lower()}"
    
    if use_cache:
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
    
    # Načtení z API
    url = f'https://pokeapi.co/api/v2/pokemon/{str(name_or_id).lower()}'
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if use_cache:
            cache.set(cache_key, data, 3600)  # Cache na 1 hodinu
        
        # Volitelně uložit do DB pro budoucí použití
        save_pokemon_to_db(data)
        return data
    
    return None


def convert_db_to_api_format(pokemon: Pokemon) -> Dict:
    """Konvertuje DB model na formát kompatibilní s původním API"""
    return {
        'id': pokemon.pokedex_id,
        'name': pokemon.name,
        'height': pokemon.height,
        'weight': pokemon.weight,
        'base_experience': pokemon.base_experience,
        'sprites': {
            'front_default': pokemon.sprite_url
        },
        'types': [
            {
                'type': {'name': type_obj.name}
            } for type_obj in pokemon.types.all()
        ],
        'abilities': [
            {
                'ability': {'name': ability.name}
            } for ability in pokemon.abilities.all()
        ],
        'stats': [
            {'stat': {'name': 'hp'}, 'base_stat': pokemon.hp},
            {'stat': {'name': 'attack'}, 'base_stat': pokemon.attack},
            {'stat': {'name': 'defense'}, 'base_stat': pokemon.defense},
            {'stat': {'name': 'special-attack'}, 'base_stat': pokemon.special_attack},
            {'stat': {'name': 'special-defense'}, 'base_stat': pokemon.special_defense},
            {'stat': {'name': 'speed'}, 'base_stat': pokemon.speed},
        ]
    }



def save_pokemon_to_db(api_data: Dict) -> Pokemon:
    """Uloží Pokémona z API dat do databáze"""
    try:
        with transaction.atomic():
            pokemon, created = Pokemon.objects.get_or_create(
                pokedex_id=api_data['id'],
                defaults={
                    'name': api_data['name'],
                    'height': api_data['height'],
                    'weight': api_data['weight'],
                    'base_experience': api_data.get('base_experience', 0),
                    'sprite_url': api_data['sprites'].get('front_default', ''),
                    'hp': next(stat['base_stat'] for stat in api_data['stats'] if stat['stat']['name'] == 'hp'),
                    'attack': next(stat['base_stat'] for stat in api_data['stats'] if stat['stat']['name'] == 'attack'),
                    'defense': next(stat['base_stat'] for stat in api_data['stats'] if stat['stat']['name'] == 'defense'),
                    'special_attack': next(stat['base_stat'] for stat in api_data['stats'] if stat['stat']['name'] == 'special-attack'),
                    'special_defense': next(stat['base_stat'] for stat in api_data['stats'] if stat['stat']['name'] == 'special-defense'),
                    'speed': next(stat['base_stat'] for stat in api_data['stats'] if stat['stat']['name'] == 'speed'),
                }
            )
            
            # Uložení typů
            for type_data in api_data.get('types', []):
                type_name = type_data['type']['name']
                pokemon_type, _ = PokemonType.objects.get_or_create(name=type_name)
                pokemon.types.add(pokemon_type)
            
            return pokemon
    except Exception as e:
        print(f"Chyba při ukládání Pokémona: {e}")
        return None


def get_all_pokemon(limit=50, use_db=True) -> List[Dict]:
    """Získá seznam Pokémonů - preferuje DB před API"""
    if use_db:
        # Nejdřív zkus z databáze
        db_pokemon = Pokemon.objects.prefetch_related('types').order_by('pokedex_id')[:limit]
        if db_pokemon.exists():
            return [convert_db_to_api_format(p) for p in db_pokemon]
    
    # Fallback na API
    url = f'https://pokeapi.co/api/v2/pokemon?limit={limit}'
    response = requests.get(url)
    
    if response.status_code == 200:
        results = response.json().get('results', [])
        return [get_pokemon(p['name']) for p in results if get_pokemon(p['name'])]
    
    return []


def get_pokemon_by_type(type_name: str, use_db=True) -> List[Dict]:
    """Získá Pokémony podle typu"""
    if use_db:
        try:
            pokemon_type = PokemonType.objects.get(name__iexact=type_name)
            db_pokemon = pokemon_type.pokemon.prefetch_related('types').order_by('pokedex_id')[:50]
            if db_pokemon.exists():
                return [convert_db_to_api_format(p) for p in db_pokemon]
        except PokemonType.DoesNotExist:
            pass
    
    # Fallback na API
    url = f'https://pokeapi.co/api/v2/type/{type_name.lower()}'
    response = requests.get(url)
    
    if response.status_code == 200:
        results = response.json().get('pokemon', [])
        return [get_pokemon(p['pokemon']['name']) for p in results[:50] if get_pokemon(p['pokemon']['name'])]
    
    return []


def get_pokemon_species(name):
    """Zachová původní funkcionalitu pro kompatibilitu"""
    url = f'https://pokeapi.co/api/v2/pokemon-species/{name.lower()}'
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None


def get_evolution_chain(url):
    """Zachová původní funkcionalitu pro kompatibilitu"""
    response = requests.get(url)
    if response.status_code != 200:
        return []
    
    chain = response.json().get('chain', {})
    
    def extract(chain):
        result = []
        while chain:
            species_name = chain['species']['name']
            result.append(species_name)
            chain = chain['evolves_to'][0] if chain['evolves_to'] else None
        return result
    
    return extract(chain)


def get_evolution_chain_from_db(pokemon_name: str) -> List[str]:
    """Získá evoluční řetězec z databáze"""
    try:
        pokemon = Pokemon.objects.get(name__iexact=pokemon_name)
        chain = [pokemon.name]
        
        # Najdi předchůdce
        current = pokemon
        while current.evolves_from.exists():
            current = current.evolves_from.first().from_pokemon
            chain.insert(0, current.name)
        
        # Najdi následníky
        current = pokemon
        while current.evolves_to.exists():
            current = current.evolves_to.first().to_pokemon
            chain.append(current.name)
        
        return chain
    except Pokemon.DoesNotExist:
        return []


def save_battle_history(user_team: List[str], cpu_team: List[str], result: str, battle_log: List[str]):
    """Uloží historii bitvy do databáze"""
    try:
        battle = BattleHistory.objects.create(
            result=result,
            battle_log='\n'.join(battle_log)
        )
        
        # Přidej týmy
        for pokemon_name in user_team:
            pokemon = get_pokemon_from_db(pokemon_name)
            if pokemon:
                battle.user_team.add(pokemon)
        
        for pokemon_name in cpu_team:
            pokemon = get_pokemon_from_db(pokemon_name)
            if pokemon:
                battle.cpu_team.add(pokemon)
        
        return battle
    except Exception as e:
        print(f"Chyba při ukládání historie bitvy: {e}")
        return None


def get_popular_pokemon(limit=10) -> List[Dict]:
    """Získá nejpopulárnější Pokémony podle počtu bitev"""
    from django.db.models import Count
    
    popular = Pokemon.objects.annotate(
        battle_count=Count('user_battles') + Count('cpu_battles')
    ).order_by('-battle_count')[:limit]
    
    return [convert_db_to_api_format(p) for p in popular]


def search_pokemon(query: str, limit=20) -> List[Dict]:
    """Vyhledá Pokémony podle jména"""
    from django.db.models import Q
    
    # Vyhledání v databázi
    pokemon_list = Pokemon.objects.filter(
        Q(name__icontains=query) | Q(types__name__icontains=query)
    ).distinct().prefetch_related('types')[:limit]
    
    return [convert_db_to_api_format(p) for p in pokemon_list]