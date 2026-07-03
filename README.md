# MyWeek

Application Django de gestion de semaine : taches, habitudes, emploi du temps, statistiques et parametres.

## Installation

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Puis ouvrir `http://127.0.0.1:8000/`.

La page d'accueil redirige vers `http://127.0.0.1:8000/connexion/` si aucun utilisateur n'est connecte. Un nouvel utilisateur peut creer son compte sur `http://127.0.0.1:8000/inscription/`.

## Lancement avec Docker

```bash
docker compose up --build
```

Puis ouvrir `http://127.0.0.1:8000/`.

La base SQLite est stockee dans un volume Docker nomme `myweek_data`.
Pour arreter l'application :

```bash
docker compose down
```

## Fonctionnalites MVP

- Dashboard avec indicateurs de la semaine.
- Connexion, inscription et deconnexion.
- Donnees separees par utilisateur.
- CRUD des taches avec priorite, statut, date et horaires.
- CRUD des habitudes avec cochage quotidien.
- Emploi du temps hebdomadaire en colonnes.
- Export PDF structure de l'emploi du temps.
- Statistiques simples mises a jour depuis les donnees.
- Parametres simples et reinitialisation locale.
