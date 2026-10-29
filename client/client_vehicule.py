"""Deplacement et communication communs aux voitures et aux urgences."""

import json
from functools import lru_cache
import socket
import threading
import time

if __package__:
    from .config import HOST, PORT
else:
    from config import HOST, PORT

_DUREE_CACHE_PARAMETRES = 60.0
_verrou_parametres = threading.Lock()
_parametres_cache: tuple[int, int, float] | None = None
_parametres_cache_expire_a = 0.0

def _get_parametre(commande: str) -> float:
    """Demande au serveur un parametre numerique de simulation."""
    try:
        with socket.create_connection((HOST, PORT)) as client:
            client.sendall((commande + "\n").encode("utf-8"))
            with client.makefile("r", encoding="utf-8") as lecteur:
                reponse = lecteur.readline()
            if not reponse:
                raise ConnectionError("Le serveur a ferme la connexion.")
            return float(reponse)
    except (OSError, ValueError, ConnectionError) as erreur:
        raise ConnectionError(f"Impossible de récupérer {commande}: {erreur}") from erreur


def get_ligne_arret() -> int:
    """Retourne la ligne d'arret configuree par le serveur."""
    return _get_parametres_simulation()[0]


def get_pas_avancement() -> int:
    """Retourne le pas d'avancement configure par le serveur."""
    return _get_parametres_simulation()[1]


def get_pas_simulation() -> float:
    """Retourne le delai de simulation configure par le serveur."""
    return _get_parametres_simulation()[2]


def _get_parametres_simulation() -> tuple[int, int, float]:
    """Retourne les parametres du serveur, actualises au plus toutes les 60 s."""
    global _parametres_cache, _parametres_cache_expire_a

    with _verrou_parametres:
        maintenant = time.monotonic()
        if _parametres_cache is None or maintenant >= _parametres_cache_expire_a:
            parametres = (
                int(_get_parametre("GET_LIGNE_ARRET")),
                int(_get_parametre("GET_PAS_AVANCEMENT")),
                _get_parametre("GET_PAS_SIMULATION"),
            )
            _parametres_cache = parametres
            _parametres_cache_expire_a = time.monotonic() + _DUREE_CACHE_PARAMETRES

        return _parametres_cache

def prochaine_position(position: int, feu: str, pas_avancement: int = 1, ligne_arret: int = 30) -> int:
    """Le vehicule choisit son prochain pas selon le feu."""
    if feu != "VERT" and position <= ligne_arret:
        return min(position + pas_avancement, ligne_arret)
    return min(position + pas_avancement, 100)


def echanger(client, lecteur, message: str) -> list[str]:
    """Envoie une commande et lit une reponse du carrefour."""
    client.sendall((message + "\n").encode("utf-8"))
    reponse = lecteur.readline()
    if not reponse:
        raise ConnectionError("Le carrefour a ferme la connexion.")
    return reponse.strip().split("|")


@lru_cache(maxsize=2)
def get_trajets(carrefour: str = "CROIX") -> dict[str, list[str]]:
    """Recupere les trajets autorises par le carrefour cible."""
    with socket.create_connection((HOST, PORT)) as client:
        with client.makefile("r", encoding="utf-8") as lecteur:
            if carrefour != "CROIX":
                selection = echanger(client, lecteur, f"CARREFOUR|{carrefour}")
                if selection != ["OK"]:
                    raise ValueError("|".join(selection))
            reponse = echanger(client, lecteur, "GET_TRAJETS")
            if reponse[0] != "TRAJETS":
                raise ValueError("|".join(reponse))
            return json.loads(reponse[1])


def simuler_vehicule(nom: str, type_vehicule: str, direction: str, manoeuvre: str, carrefour: str = "CROIX") -> None:
    """Fait rouler un vehicule jusqu'a la sortie du carrefour."""
    try:
        ligne_arret = get_ligne_arret()
        pas_avancement = get_pas_avancement()
        pas_simulation = get_pas_simulation()
        with socket.create_connection((HOST, PORT)) as client:
            with client.makefile("r", encoding="utf-8") as lecteur:
                if carrefour != "CROIX":
                    selection = echanger(client, lecteur, f"CARREFOUR|{carrefour}")
                    if selection != ["OK"]:
                        raise ValueError("|".join(selection))
                position = 0
                while True:
                    identite = f"IDENTITE|{nom}|{type_vehicule}|{direction}|{manoeuvre}|{position}"
                    reponse = echanger(client, lecteur, identite)
                    if reponse == ["OK"]:
                        break
                    if reponse[0] != "ATTENTE":
                        raise ValueError("|".join(reponse))
                    position -= 1
                print(f"{nom} arrive par {direction} ({manoeuvre.lower()}).")

                if type_vehicule == "urgence":
                    echanger(client, lecteur, "URGENCE")
                    print(f"{nom} a la priorite.")

                while position < 100:
                    feu = echanger(client, lecteur, "ETAT")[2]
                    demande = prochaine_position(position, feu, pas_avancement, ligne_arret)
                    reponse = echanger(client, lecteur, f"POSITION|{demande}")

                    if reponse == ["ATTENTE"]:
                        print(f"{nom} attend a {position} %.")
                    else:
                        position = demande
                        print(f"{nom} : progression {max(0, position)} %")
                    time.sleep(pas_simulation)

                client.sendall(b"TERMINE\n")
                print(f"{nom} a traverse le carrefour.")
    except (OSError, IndexError, ValueError, ConnectionError) as erreur:
        print(f"{nom} : {erreur}")
