from django.test import TestCase
from unittest.mock import patch
from django.urls import reverse
from .services import (
    get_pokemon,
    get_all_pokemon,
    get_pokemon_species,
    get_evolution_chain,
    get_pokemon_by_type
)


class PokemonServiceTests(TestCase):

    @patch('Main.services.requests.get')
    def test_get_pokemon_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'name': 'pikachu'}
        result = get_pokemon('pikachu')
        self.assertEqual(result['name'], 'pikachu')

    @patch('Main.services.requests.get')
    def test_get_pokemon_failure(self, mock_get):
        mock_get.return_value.status_code = 404
        result = get_pokemon('missingno')
        self.assertIsNone(result)

    @patch('Main.services.get_pokemon')
    @patch('Main.services.requests.get')
    def test_get_all_pokemon(self, mock_get, mock_get_pokemon):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'results': [{'name': 'pikachu'}, {'name': 'bulbasaur'}]
        }
        mock_get_pokemon.side_effect = lambda name: {'name': name}
        result = get_all_pokemon(limit=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'pikachu')

    @patch('Main.services.requests.get')
    def test_get_pokemon_species_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'evolution_chain': {'url': 'some-url'}}
        result = get_pokemon_species('pikachu')
        self.assertIn('evolution_chain', result)

    @patch('Main.services.requests.get')
    def test_get_pokemon_species_failure(self, mock_get):
        mock_get.return_value.status_code = 404
        result = get_pokemon_species('unknown')
        self.assertIsNone(result)

    @patch('Main.services.requests.get')
    def test_get_evolution_chain(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'chain': {
                'species': {'name': 'bulbasaur'},
                'evolves_to': [{
                    'species': {'name': 'ivysaur'},
                    'evolves_to': [{
                        'species': {'name': 'venusaur'},
                        'evolves_to': []
                    }]
                }]
            }
        }
        result = get_evolution_chain('some-url')
        self.assertEqual(result, ['bulbasaur', 'ivysaur', 'venusaur'])

    @patch('Main.services.get_pokemon')
    @patch('Main.services.requests.get')
    def test_get_pokemon_by_type(self, mock_get, mock_get_pokemon):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'pokemon': [{'pokemon': {'name': 'pikachu'}}, {'pokemon': {'name': 'raichu'}}]
        }
        mock_get_pokemon.side_effect = lambda name: {'name': name}
        result = get_pokemon_by_type('electric')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'pikachu')

class PokemonViewsTest(TestCase):

    @patch('Main.views.get_pokemon_by_type')
    @patch('Main.views.get_all_pokemon')
    def test_index_view(self, mock_get_all_pokemon, mock_get_pokemon_by_type):
        mock_get_all_pokemon.return_value = [{'name': 'pikachu'}]
        mock_get_pokemon_by_type.return_value = [{'name': 'charmander'}]

        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['pokemons'], [{'name': 'pikachu'}])

        response = self.client.get(reverse('index') + '?type=fire')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['pokemons'], [{'name': 'charmander'}])

    @patch('Main.views.get_pokemon')
    @patch('Main.views.get_pokemon_species')
    @patch('Main.views.get_evolution_chain')
    def test_pokemon_detail(self, mock_get_evolution_chain, mock_get_pokemon_species, mock_get_pokemon):
        mock_get_pokemon.return_value = {'name': 'bulbasaur'}
        mock_get_pokemon_species.return_value = {'evolution_chain': {'url': 'fake_url'}}
        mock_get_evolution_chain.return_value = ['bulbasaur', 'ivysaur']

        url = reverse('pokemon_detail', kwargs={'name': 'bulbasaur'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['pokemon']['name'], 'bulbasaur')
        self.assertEqual(response.context['evolution'], ['bulbasaur', 'ivysaur'])

    @patch('Main.views.get_pokemon')
    def test_compare_pokemons(self, mock_get_pokemon):
        def side_effect(name):
            return {'name': name, 'stats': [{'stat': {'name': 'hp'}, 'base_stat': 45}]}
        mock_get_pokemon.side_effect = side_effect

        url = reverse('compare') + '?p1=pikachu&p2=bulbasaur'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['p1']['name'], 'pikachu')
        self.assertEqual(response.context['p2']['name'], 'bulbasaur')
