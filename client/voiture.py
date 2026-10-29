"""Generation de voitures suivant les trajets autorises par le serveur."""

import argparse
import random
import threading
import time
import uuid

if __package__:
    from .client_vehicule import get_trajets, simuler_vehicule
else:
    from client_vehicule import get_trajets, simuler_vehicule


def simuler_voiture(numero: int, carrefour: str = "CROIX"):
    trajets = get_trajets(carrefour)
    directions = tuple(trajets)
    direction = directions[(numero - 1) % len(directions)]
    manoeuvre = random.choice(trajets[direction])
    nom = f"Voiture-{carrefour}-{numero}-{uuid.uuid4().hex[:8]}"
    simuler_vehicule(nom, "voiture", direction, manoeuvre, carrefour)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("densite", nargs="?", type=int, default=3)
    parser.add_argument("--carrefour", type=str.upper, choices=("CROIX", "T"), default="CROIX")
    args = parser.parse_args()
    if args.densite < 1:
        parser.error("La densite des voitures doit etre un entier positif.")
    try:
        get_trajets(args.carrefour)
        delai = max(1.0, 6.0 / args.densite)
        numero = 1
        while True:
            voiture = threading.Thread(target=simuler_voiture, args=(numero, args.carrefour), daemon=True)
            voiture.start()
            numero += 1
            time.sleep(delai)
    except KeyboardInterrupt:
        print("Simulation interrompue par l'utilisateur.")
    except (OSError, ValueError) as erreur:
        parser.exit(1, f"Impossible de lancer les voitures : {erreur}\n")


if __name__ == "__main__":
    main()
