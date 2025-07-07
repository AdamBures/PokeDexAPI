# PokeDexAPI

This Django project is a Pokémon-themed web application featuring a comprehensive Pokédex, detailed Pokémon views, comparison functionality, a battle arena, and battle history tracking.

## Features

- **Pokédex Listing**  
  Browse all Pokémon with filters by type, sorting by various stats (ID, name, HP, attack, total stats), and pagination.

- **Pokémon Detail View**  
  View detailed info on a Pokémon, including its evolution chain, similar Pokémon by type, and recent battle history.

- **Pokémon Comparison**  
  Compare stats of two Pokémon side-by-side with random recommendations for pairs to compare.

- **Search**  
  Search Pokémon by name with case-insensitive partial matching.

- **Battle Arena**  
  Select a team of 3 Pokémon to battle against a computer’s 3 randomly chosen Pokémon. Battles simulate turn-based combat factoring in stats and type effectiveness. Battle logs and results are saved and shown.

- **Battle History**  
  View paginated history of battles with win/loss/draw stats and overall win rates.

## Views Overview

- `index(request)`  
  Main Pokédex page with type filters, sorting options, and pagination.

- `pokemon_detail(request, name)`  
  Detailed Pokémon info, evolution chain, similar Pokémon, recent battles.

- `compare_pokemons(request)`  
  Compare two Pokémon’s stats with merged views and winner indication.

- `search(request)`  
  Search Pokémon by name returning matching results.

- `arena(request)`  
  Battle arena for selecting teams, running battles, showing logs, and statistics; supports pagination for Pokémon selection.

- `battle_history(request)`  
  Paginated list of past battles with summary statistics.

## Technologies and Libraries

- Django ORM for efficient database interactions  
- Django templates for frontend rendering  
- Django Paginator for pagination  
- CSRF exemption for arena POST requests (to allow battle submissions)  
- Custom battle logic with simplified type effectiveness and random damage variation

## Installation

1. Download or clone the project repository (zip file from GitHub).

2. Import Pokémon data into the database with the custom management command:

   ```bash
   python manage.py import_pokemon
   ```

3. Run the development server

  ```bash
  python manage.py runserver
  ```
## Docker Installation

You can easily build and run the Pokémon application using Docker.

### Build and Run

1. Build the Docker image:

   ```bash
   docker-compose build
   ```
2. Start the container
   ```bash
   docker-compose up
   ```
3. The app will be available at http://localhost:8000.
