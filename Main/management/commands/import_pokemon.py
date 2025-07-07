import requests
from django.core.management.base import BaseCommand
from Main.models import Pokemon, PokemonType, Ability, Evolution

class Command(BaseCommand):
    help = 'Import Pokémonů z PokeAPI (prvních 150)'

    def parse_evolution_chain(self, chain_node):
        """Rekurzivně rozparsuje evoluční řetězec z PokeAPI do seznamu jmen."""
        evolutions = [chain_node['species']['name']]
        for evo in chain_node.get('evolves_to', []):
            evolutions.extend(self.parse_evolution_chain(evo))
        return evolutions

    def save_evolutions(self, evolutions_list):
        """
        Uloží evoluce do DB podle pořadí v seznamu.
        evolutions_list = ['bulbasaur', 'ivysaur', 'venusaur']
        """
        for i in range(len(evolutions_list) - 1):
            from_name = evolutions_list[i]
            to_name = evolutions_list[i + 1]
            try:
                from_pokemon = Pokemon.objects.get(name=from_name)
                to_pokemon = Pokemon.objects.get(name=to_name)
                Evolution.objects.get_or_create(from_pokemon=from_pokemon, to_pokemon=to_pokemon)
            except Pokemon.DoesNotExist:
                pass

    def handle(self, *args, **kwargs):
        url = 'https://pokeapi.co/api/v2/pokemon?limit=150'
        response = requests.get(url)
        if response.status_code != 200:
            self.stdout.write(self.style.ERROR('Nepodařilo se stáhnout seznam Pokémonů'))
            return

        data = response.json()
        results = data['results']

        for pokemon_entry in results:
            poke_url = pokemon_entry['url']
            poke_response = requests.get(poke_url)
            if poke_response.status_code != 200:
                self.stdout.write(self.style.WARNING(f'Nepodařilo se stáhnout data pro {pokemon_entry["name"]}'))
                continue

            poke_data = poke_response.json()

            pokedex_id = poke_data['id']
            name = poke_data['name']
            height = poke_data['height']  # decimetry
            weight = poke_data['weight']  # hectogramy
            base_experience = poke_data.get('base_experience', 0)
            sprite_url = poke_data['sprites']['front_default']

            # stats mapping podle tvého modelu
            stats = {stat['stat']['name']: stat['base_stat'] for stat in poke_data['stats']}
            hp = stats.get('hp', 1)
            attack = stats.get('attack', 1)
            defense = stats.get('defense', 1)
            special_attack = stats.get('special-attack', 1)
            special_defense = stats.get('special-defense', 1)
            speed = stats.get('speed', 1)

            # Určení, jestli je legendární nebo mytický (z "species" endpointu)
            species_url = poke_data['species']['url']
            species_response = requests.get(species_url)
            is_legendary = False
            is_mythical = False
            if species_response.status_code == 200:
                species_data = species_response.json()
                is_legendary = species_data.get('is_legendary', False)
                is_mythical = species_data.get('is_mythical', False)

            # Vytvoření nebo update Pokémona
            pokemon_obj, created = Pokemon.objects.update_or_create(
                pokedex_id=pokedex_id,
                defaults={
                    'name': name,
                    'height': height,
                    'weight': weight,
                    'base_experience': base_experience,
                    'sprite_url': sprite_url,
                    'hp': hp,
                    'attack': attack,
                    'defense': defense,
                    'special_attack': special_attack,
                    'special_defense': special_defense,
                    'speed': speed,
                    'is_legendary': is_legendary,
                    'is_mythical': is_mythical,
                }
            )

            # Nastavení typů
            pokemon_obj.types.clear()
            color_map = {
                'normal': '#A8A77A',
                'fire': '#EE8130',
                'water': '#6390F0',
                'electric': '#F7D02C',
                'grass': '#7AC74C',
                'ice': '#96D9D6',
                'fighting': '#C22E28',
                'poison': '#A33EA1',
                'ground': '#E2BF65',
                'flying': '#A98FF3',
                'psychic': '#F95587',
                'bug': '#A6B91A',
                'rock': '#B6A136',
                'ghost': '#735797',
                'dragon': '#6F35FC',
                'dark': '#705746',
                'steel': '#B7B7CE',
                'fairy': '#D685AD',
            }
            for t in poke_data['types']:
                type_name = t['type']['name']
                color = color_map.get(type_name, '#000000')
                type_obj, _ = PokemonType.objects.get_or_create(name=type_name, defaults={'color': color})
                pokemon_obj.types.add(type_obj)

            # Nastavení schopností (abilities)
            pokemon_obj.abilities.clear()
            for ability_info in poke_data['abilities']:
                ability_name = ability_info['ability']['name']
                ability_obj, _ = Ability.objects.get_or_create(name=ability_name)
                pokemon_obj.abilities.add(ability_obj)

            # Import evolučního řetězce
            if species_response.status_code == 200:
                evo_chain_url = species_data['evolution_chain']['url']
                evo_chain_response = requests.get(evo_chain_url)
                if evo_chain_response.status_code == 200:
                    evo_chain_data = evo_chain_response.json()
                    evolutions = self.parse_evolution_chain(evo_chain_data['chain'])
                    self.save_evolutions(evolutions)

            self.stdout.write(f'Importován Pokémon: {name} (#{pokedex_id})')

        self.stdout.write(self.style.SUCCESS('Import dokončen!'))
