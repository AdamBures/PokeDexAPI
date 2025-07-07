# views.py
import random
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib import messages
from .models import Pokemon, PokemonType, BattleHistory
from .services import (
    get_pokemon,
    get_all_pokemon,
    get_pokemon_species,
    get_evolution_chain,
    get_pokemon_by_type,
    save_battle_history,
    get_popular_pokemon,
    search_pokemon,
    get_pokemon_from_db,
    convert_db_to_api_format
)


def index(request):
    """Hlavní stránka s filtry a paginací"""
    type_filter = request.GET.get('type')
    sort_by = request.GET.get('sort', 'pokedex_id')
    page = request.GET.get('page', 1)
    
    # Použij ORM pro efektivní dotazy
    pokemon_queryset = Pokemon.objects.prefetch_related('types').all()
    
    # Filtrování podle typu
    if type_filter:
        pokemon_queryset = pokemon_queryset.filter(types__name__iexact=type_filter)
    
    # Řazení
    sort_options = {
        'pokedex_id': 'pokedex_id',
        'name': 'name',
        'hp': '-hp',
        'attack': '-attack',
        'total_stats': '-hp',  # Placeholder - použijeme vlastní řazení
    }
    
    if sort_by in sort_options:
        if sort_by == 'total_stats':
            # Řazení podle celkových statistik
            pokemon_queryset = pokemon_queryset.extra(
                select={'total': 'hp + attack + defense + special_attack + special_defense + speed'}
            ).order_by('-total')
        else:
            pokemon_queryset = pokemon_queryset.order_by(sort_options[sort_by])
    
    # Paginace
    paginator = Paginator(pokemon_queryset, 20)
    pokemon_page = paginator.get_page(page)
    
    # Konverze na API formát pro kompatibilitu s templates
    pokemons = [convert_db_to_api_format(p) for p in pokemon_page]
    
    # Získání všech typů pro filter
    all_types = PokemonType.objects.all().order_by('name')
    
    context = {
        'pokemons': pokemons,
        'pokemon_page': pokemon_page,
        'all_types': all_types,
        'current_type': type_filter,
        'current_sort': sort_by,
        'sort_options': [
            ('pokedex_id', 'Podle čísla'),
            ('name', 'Podle jména'),
            ('hp', 'Podle HP'),
            ('attack', 'Podle útoku'),
            ('total_stats', 'Podle celkových statistik'),
        ]
    }
    
    return render(request, 'index.html', context)


def pokemon_detail(request, name):
    """Detail Pokémona s optimalizovanými dotazy"""
    # Zkus najít v DB nejdřív
    pokemon_db = get_pokemon_from_db(name)
    
    if pokemon_db:
        pokemon = convert_db_to_api_format(pokemon_db)
        
        # Evoluce z DB
        evolution_chain = []
        current = pokemon_db
        
        # Najdi celý evoluční řetězec
        while current.evolves_from.exists():
            current = current.evolves_from.first().from_pokemon
        
        # Projdi řetězec vpřed
        evolution_chain.append(current.name)
        while current.evolves_to.exists():
            current = current.evolves_to.first().to_pokemon
            evolution_chain.append(current.name)
        
        # Statistiky podobných Pokémonů
        similar_pokemon = Pokemon.objects.filter(
            types__in=pokemon_db.types.all()
        ).exclude(
            id=pokemon_db.id
        ).distinct()[:5]
        
        similar_pokemon_api = [convert_db_to_api_format(p) for p in similar_pokemon]
        
    else:
        # Fallback na API
        pokemon = get_pokemon(name)
        if not pokemon:
            return render(request, '404.html', status=404)
        
        species = get_pokemon_species(name)
        evolution_chain = get_evolution_chain(species['evolution_chain']['url']) if species else []
        similar_pokemon_api = []
    
    # Historie bitev s tímto Pokémonem
    battle_history = []
    if pokemon_db:
        recent_battles = BattleHistory.objects.filter(
            Q(user_team=pokemon_db) | Q(cpu_team=pokemon_db)
        ).order_by('-created_at')[:5]
        
        battle_history = [
            {
                'date': battle.created_at,
                'result': battle.get_result_display(),
                'id': battle.id
            }
            for battle in recent_battles
        ]
    
    context = {
        'pokemon': pokemon,
        'evolution': evolution_chain,
        'similar_pokemon': similar_pokemon_api,
        'battle_history': battle_history,
    }
    
    return render(request, 'detail.html', context)


def compare_pokemons(request):
    """Porovnání Pokémonů s uložením do historie"""
    name1 = request.GET.get('p1')
    name2 = request.GET.get('p2')
    
    p1 = get_pokemon(name1) if name1 else None
    p2 = get_pokemon(name2) if name2 else None
    
    merged_stats = []
    comparison_result = None
    
    if p1 and p2:
        # Převod statistik na slovník
        p1_stats = {s["stat"]["name"]: s["base_stat"] for s in p1["stats"]}
        p2_stats = {s["stat"]["name"]: s["base_stat"] for s in p2["stats"]}
        
        # Sjednocený seznam všech názvů statistik
        all_stat_names = set(p1_stats) | set(p2_stats)
        
        # Sloučení do jednoho seznamu slovníků
        merged_stats = [
            {
                "name": stat,
                "p1": p1_stats.get(stat, 0),
                "p2": p2_stats.get(stat, 0),
                "winner": "p1" if p1_stats.get(stat, 0) > p2_stats.get(stat, 0) else "p2" if p2_stats.get(stat, 0) > p1_stats.get(stat, 0) else "tie"
            }
            for stat in all_stat_names
        ]
        
        # Celkové porovnání
        p1_total = sum(p1_stats.values())
        p2_total = sum(p2_stats.values())
        
        if p1_total > p2_total:
            comparison_result = f"{p1['name'].capitalize()} má celkově lepší statistiky ({p1_total} vs {p2_total})"
        elif p2_total > p1_total:
            comparison_result = f"{p2['name'].capitalize()} má celkově lepší statistiky ({p2_total} vs {p1_total})"
        else:
            comparison_result = "Pokémoni mají stejné celkové statistiky"
    
    # Doporučené porovnání
    recommended_pairs = []
    if Pokemon.objects.exists():
        random_pokemon = Pokemon.objects.order_by('?')[:4]
        recommended_pairs = [
            (random_pokemon[0].name, random_pokemon[1].name),
            (random_pokemon[2].name, random_pokemon[3].name) if len(random_pokemon) > 3 else None
        ]
        recommended_pairs = [pair for pair in recommended_pairs if pair]
    
    context = {
        'p1': p1,
        'p2': p2,
        'merged_stats': merged_stats,
        'comparison_result': comparison_result,
        'recommended_pairs': recommended_pairs
    }
    
    return render(request, 'compare.html', context)


def search(request):
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        # Vyhledávání, kde jméno obsahuje query (case-insensitive)
        results = Pokemon.objects.filter(name__icontains=query).order_by('pokedex_id')[:20]

    context = {
        'results': results,
        'query': query,
    }
    return render(request, 'search.html', context)



def calculate_attack(attacker, defender):
    """Výpočet útoku s type effectiveness"""
    attack = next(stat['base_stat'] for stat in attacker['stats'] if stat['stat']['name'] == 'attack')
    defense = next(stat['base_stat'] for stat in defender['stats'] if stat['stat']['name'] == 'defense')
    
    # Základní damage
    damage = max(0, attack - defense + random.randint(-5, 5))
    
    # Type effectiveness (zjednodušené)
    attacker_types = [t['type']['name'] for t in attacker.get('types', [])]
    defender_types = [t['type']['name'] for t in defender.get('types', [])]
    
    # Jednoduchá type effectiveness
    effectiveness = 1.0
    type_chart = {
        'fire': {'grass': 2.0, 'water': 0.5, 'fire': 0.5},
        'water': {'fire': 2.0, 'grass': 0.5, 'water': 0.5},
        'grass': {'water': 2.0, 'fire': 0.5, 'grass': 0.5},
        'electric': {'water': 2.0, 'grass': 0.5, 'electric': 0.5},
    }
    
    for att_type in attacker_types:
        for def_type in defender_types:
            if att_type in type_chart and def_type in type_chart[att_type]:
                effectiveness *= type_chart[att_type][def_type]
    
    return int(damage * effectiveness)


@csrf_exempt
def arena(request):
    """Vylepšená aréna s výběrem Pokémonů a stránkováním"""
    
    # Načti všechny Pokémony z DB
    all_pokemon_db = Pokemon.objects.prefetch_related('types').order_by('pokedex_id')
    paginator = Paginator(all_pokemon_db, 30)  # 30 Pokémonů na stránku

    # Získání čísla stránky z GET parametru
    page_number = request.GET.get('page') or 1
    page_obj = paginator.get_page(page_number)

    # Převedení na API formát pro použití v šabloně
    all_pokemon = [convert_db_to_api_format(p) for p in page_obj]

    # Inicializace proměnných
    battle_log = []
    user_team = []
    cpu_team = []
    winner = None
    battle_id = None

    if request.method == 'POST':
        selected = request.POST.getlist('selected')[:3]
        
        if len(selected) != 3:
            messages.error(request, "Musíš vybrat přesně 3 Pokémony!")
        else:
            user_team = [get_pokemon(name) for name in selected]
            available_names = [p['name'] for p in all_pokemon if p['name'] not in selected]
            cpu_names = random.sample(available_names, 3)
            cpu_team = [get_pokemon(name) for name in cpu_names]
            
            # Inicializace HP
            for p in user_team + cpu_team:
                base_hp = next(stat['base_stat'] for stat in p['stats'] if stat['stat']['name'] == 'hp')
                p['hp'] = base_hp
                p['max_hp'] = base_hp
            
            battle_log.append("=== PRŮBĚH BITVY ===")
            
            # Bitva
            user_idx = 0
            cpu_idx = 0
            
            while user_idx < len(user_team) and cpu_idx < len(cpu_team):
                current_user = user_team[user_idx]
                current_cpu = cpu_team[cpu_idx]
                
                battle_log.append(f"🆚 {current_user['name'].capitalize()} vs {current_cpu['name'].capitalize()}")
                
                while current_user['hp'] > 0 and current_cpu['hp'] > 0:
                    user_speed = next(stat['base_stat'] for stat in current_user['stats'] if stat['stat']['name'] == 'speed')
                    cpu_speed = next(stat['base_stat'] for stat in current_cpu['stats'] if stat['stat']['name'] == 'speed')
                    
                    if user_speed >= cpu_speed:
                        damage = calculate_attack(current_user, current_cpu)
                        current_cpu['hp'] -= damage
                        current_cpu['hp'] = max(0, current_cpu['hp'])
                        battle_log.append(f"⚔️ {current_user['name'].capitalize()} útočí za {damage} poškození! (Oponent HP: {current_cpu['hp']})")
                        
                        if current_cpu['hp'] > 0:
                            damage = calculate_attack(current_cpu, current_user)
                            current_user['hp'] -= damage
                            current_user['hp'] = max(0, current_user['hp'])
                            battle_log.append(f"💥 {current_cpu['name'].capitalize()} útočí za {damage} poškození! (Tvůj HP: {current_user['hp']})")
                    else:
                        damage = calculate_attack(current_cpu, current_user)
                        current_user['hp'] -= damage
                        current_user['hp'] = max(0, current_user['hp'])
                        battle_log.append(f"💥 {current_cpu['name'].capitalize()} útočí za {damage} poškození! (Tvůj HP: {current_user['hp']})")
                        
                        if current_user['hp'] > 0:
                            damage = calculate_attack(current_user, current_cpu)
                            current_cpu['hp'] -= damage
                            current_cpu['hp'] = max(0, current_cpu['hp'])
                            battle_log.append(f"⚔️ {current_user['name'].capitalize()} útočí za {damage} poškození! (Oponent HP: {current_cpu['hp']})")
                
                if current_user['hp'] <= 0:
                    battle_log.append(f"💀 {current_user['name'].capitalize()} byl poražen!")
                    user_idx += 1
                if current_cpu['hp'] <= 0:
                    battle_log.append(f"💀 {current_cpu['name'].capitalize()} byl poražen!")
                    cpu_idx += 1
            
            # Výsledek
            if user_idx >= len(user_team):
                winner = "💀 Počítač vyhrál!"
                result = "lose"
            elif cpu_idx >= len(cpu_team):
                winner = "🎉 Tví pokémoni vyhráli!"
                result = "win"
            else:
                winner = "🤝 Remíza!"
                result = "draw"
            
            battle_log.append("=" * 30)
            battle_log.append(winner)
            
            battle = save_battle_history(
                user_team=[p['name'] for p in user_team],
                cpu_team=[p['name'] for p in cpu_team],
                result=result,
                battle_log=battle_log
            )
            
            if battle:
                battle_id = battle.id
                messages.success(request, f"Bitva byla uložena! (ID: {battle_id})")

    # Statistiky
    arena_stats = {
        'total_battles': BattleHistory.objects.count(),
        'win_rate': 0,
        'most_used_pokemon': []
    }

    if BattleHistory.objects.exists():
        total_battles = BattleHistory.objects.count()
        wins = BattleHistory.objects.filter(result='win').count()
        arena_stats['win_rate'] = round((wins / total_battles) * 100, 1) if total_battles > 0 else 0
        arena_stats['most_used_pokemon'] = get_popular_pokemon(5)

    return render(request, 'arena.html', {
        'pokemons': all_pokemon,
        'battle_log': battle_log,
        'winner': winner,
        'user_team': user_team,
        'cpu_team': cpu_team,
        'battle_id': battle_id,
        'arena_stats': arena_stats,
        'page_obj': page_obj,
    })


def battle_history(request):
    """Zobrazení historie bitev"""
    battles = BattleHistory.objects.prefetch_related(
        'user_team', 'cpu_team'
    ).order_by('-created_at')
    
    # Paginace
    paginator = Paginator(battles, 10)
    page = request.GET.get('page', 1)
    battles_page = paginator.get_page(page)
    
    # Statistiky
    stats = {
        'total_battles': battles.count(),
        'wins': battles.filter(result='win').count(),
        'losses': battles.filter(result='lose').count(),
        'draws': battles.filter(result='draw').count(),
    }
    
    if stats['total_battles'] > 0:
        stats['win_percentage'] = round((stats['wins'] / stats['total_battles']) * 100, 1)
    else:
        stats['win_percentage'] = 0
    
    context = {
        'battles': battles_page,
        'stats': stats
    }
    
    return render(request, 'battle_history.html', context)


def battle_detail(request, battle_id):
    """Detail konkrétní bitvy"""
    battle = get_object_or_404(BattleHistory, id=battle_id)
    
    context = {
        'battle': battle,
        'user_team': battle.user_team.all(),
        'cpu_team': battle.cpu_team.all(),
        'battle_log': battle.battle_log.split('\n')
    }
    
    return render(request, 'battle_detail.html', context)