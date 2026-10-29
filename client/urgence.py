"""Client representant un vehicule prioritaire."""

import argparse
import random
import time

if __package__:
    from .client_vehicule import get_trajets, simuler_vehicule
else:
    from client_vehicule import get_trajets, simuler_vehicule


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nom", nargs="?", default="Ambulance")
    parser.add_argument("direction", nargs="?", type=str.upper)
    parser.add_argument("manoeuvre", nargs="?", type=str.upper)
    parser.add_argument("--carrefour", type=str.upper, choices=("CROIX", "T"), default="CROIX")
    parser.add_argument("--generer", type=float, metavar="DENSITE")
    args = parser.parse_args()
    if args.generer is not None and not 0 <= args.generer <= 1:
        parser.error("La densite des ambulances doit etre comprise entre 0 et 1.")
    try:
        if args.generer is not None:
            if args.generer == 0:
                return
            trajets = get_trajets(args.carrefour)
            numero = 1
            while True:
                intervalle_moyen = 6 / args.generer
                time.sleep(random.uniform(intervalle_moyen * 0.5, intervalle_moyen * 1.5))
                direction = random.choice(tuple(trajets))
                manoeuvre = random.choice(trajets[direction])
                simuler_vehicule(f"Ambulance-{args.carrefour}-{numero}", "urgence",
                                 direction, manoeuvre, args.carrefour)
                numero += 1
        else:
            direction = args.direction or ("S" if args.carrefour == "T" else "N")
            trajets = get_trajets(args.carrefour)
            manoeuvre = args.manoeuvre or next(iter(trajets.get(direction, ())), "")
            if direction not in trajets or manoeuvre not in trajets[direction]:
                parser.error("Ce trajet n'existe pas sur le carrefour choisi.")
            simuler_vehicule(args.nom, "urgence", direction, manoeuvre, args.carrefour)
    except KeyboardInterrupt:
        print("Generation des urgences interrompue.")
    except (OSError, ValueError) as erreur:
        parser.exit(1, f"Impossible de lancer l'urgence : {erreur}\n")


if __name__ == "__main__":
    main()
