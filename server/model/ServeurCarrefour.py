"""Transport TCP et stockage des etats calcules par les clients vehicules."""

import json
from math import isfinite
import socket
import threading

from server.config import BIND_HOST, PORT
from server.model.EtatCarrefour import EtatCarrefour
from server.model.Vehicule import Vehicule


class ServeurCarrefour:
    """Gere les connexions ; les decisions de conduite appartiennent aux clients."""

    def __init__(self, etat: EtatCarrefour, host=BIND_HOST, port=PORT, etat_t=None):
        if not isinstance(etat, EtatCarrefour):
            raise TypeError("etat doit etre une instance de EtatCarrefour")
        self.etat, self.host, self.port = etat, host, port
        self.carrefours = {etat.type_carrefour: self}
        if etat_t is not None:
            if not isinstance(etat_t, EtatCarrefour) or etat_t.type_carrefour != 'T' or etat_t is etat:
                raise ValueError("etat_t doit etre un etat distinct de type T")
            self.carrefours['T'] = ServeurCarrefour(etat_t, host, port)
        self.socket_serveur = None
        self.arret = threading.Event()

    def demarrer(self):
        self.socket_serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_serveur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.socket_serveur.bind((self.host, self.port))
            self.port = self.socket_serveur.getsockname()[1]
            self.socket_serveur.listen()
        except OSError:
            self.socket_serveur.close()
            raise
        print(f"Serveur du carrefour en ecoute sur {self.host}:{self.port}")
        threading.Thread(target=self._accepter_clients, daemon=True).start()

    def _accepter_clients(self):
        while not self.arret.is_set():
            try:
                client, _ = self.socket_serveur.accept()
                threading.Thread(target=self._gerer_client, args=(client,), daemon=True).start()
            except OSError:
                break

    @staticmethod
    def _envoyer(client, message):
        client.sendall((message + '\n').encode('utf-8'))

    @staticmethod
    def _lire_rapport(contenu):
        """Verifie seulement le format reseau, jamais une trajectoire ou une collision."""
        paquet = json.loads(contenu)
        revision = paquet['revision']
        if type(revision) is not int:
            raise ValueError('Revision invalide')
        voiture = Vehicule(**paquet['vehicule'])
        if not all(isinstance(v, str) and v for v in (voiture.nom, voiture.type_vehicule, voiture.direction, voiture.manoeuvre)):
            raise ValueError('Identite invalide')
        if voiture.type_vehicule not in ('voiture', 'urgence'):
            raise ValueError('Type de vehicule invalide')
        for nom in ('engagee', 'prioritaire', 'dans_carrefour', 'retour_voie', 'depassement_droite'):
            if type(getattr(voiture, nom)) is not bool:
                raise ValueError('Indicateur invalide')
        for nom in ('progression', 'temps_attente', 'decalage_urgence', 'preparation_depassement'):
            valeur = getattr(voiture, nom)
            if type(valeur) not in (int, float) or not isfinite(valeur):
                raise ValueError('Nombre invalide')
        pose = voiture.position_affichage
        if (not isinstance(pose, (list, tuple)) or len(pose) != 5
                or not all(type(v) in (int, float) and isfinite(v) for v in pose)
                or pose[3] <= 0 or pose[4] <= 0 or voiture.temps_attente < 0):
            raise ValueError('Position graphique invalide')
        voiture.position_affichage = tuple(pose)
        return revision, voiture

    def _enregistrer_rapport(self, contenu, precedente=None):
        revision, voiture = self._lire_rapport(contenu)
        with self.etat.verrou:
            if precedente is not None:
                champs = ('nom', 'type_vehicule', 'direction', 'manoeuvre', 'prioritaire')
                if any(getattr(voiture, c) != getattr(precedente, c) for c in champs):
                    raise ValueError('Identite de connexion differente')
            elif (voiture.nom in self.etat.vehicules or voiture.prioritaire
                  or voiture.direction not in self.etat.trajets
                  or voiture.manoeuvre not in self.etat.trajets[voiture.direction]):
                raise ValueError('Identite ou trajet interdit pour ce carrefour')
            # Deux clients ne peuvent pas publier un mouvement base sur le meme
            # ancien etat : le second recupere un nouvel instantane et recalcule.
            if revision != self.etat.revision:
                return None
            if precedente is None:
                voiture.identifiant_affichage = self.etat.creer_identifiant_affichage()
            else:
                if voiture.temps_attente < precedente.temps_attente:
                    raise ValueError('Compteur d\'attente incoherent')
                voiture.identifiant_affichage = precedente.identifiant_affichage
            attente_avant = precedente.temps_attente if precedente else 0
            self.etat.temps_attente_total += voiture.temps_attente - attente_avant
            champs_traffic = ('progression', 'engagee', 'dans_carrefour', 'decalage_urgence',
                              'retour_voie', 'depassement_droite', 'preparation_depassement',
                              'position_affichage')
            trafic_modifie = precedente is None or any(
                getattr(voiture, c) != getattr(precedente, c) for c in champs_traffic)
            self.etat.vehicules[voiture.nom] = voiture
            # Un simple compteur d'attente ne change pas la situation de conduite.
            if trafic_modifie:
                self.etat.revision += 1
        self.etat.notifier()
        return voiture

    def _gerer_client(self, client):
        vehicule = None
        gestionnaire = self
        try:
            with client, client.makefile('r', encoding='utf-8') as lecteur:
                for ligne in lecteur:
                    commande, _, contenu = ligne.strip().partition('|')
                    try:
                        if commande == 'CARREFOUR':
                            if vehicule is not None or contenu not in self.carrefours:
                                raise ValueError('Carrefour indisponible ou vehicule deja inscrit')
                            gestionnaire = self.carrefours[contenu]
                            self._envoyer(client, 'OK')
                        elif commande == 'GET_TRAJETS':
                            self._envoyer(client, 'TRAJETS|' + json.dumps(gestionnaire.etat.trajets))
                        elif commande == 'INSTANTANE':
                            self._envoyer(client, 'INSTANTANE|' + json.dumps(gestionnaire.etat.instantane()))
                        elif commande in ('IDENTITE', 'POSITION'):
                            if (commande == 'IDENTITE') != (vehicule is None):
                                raise ValueError('Etat de connexion invalide')
                            recu = gestionnaire._enregistrer_rapport(contenu, vehicule)
                            if recu is None:
                                self._envoyer(client, 'REESSAYER')
                            else:
                                vehicule = recu
                                self._envoyer(client, 'OK')
                        elif commande == 'URGENCE' and vehicule is not None:
                            with gestionnaire.etat.verrou:
                                vehicule.prioritaire = True
                                gestionnaire.etat.changer_feux(vehicule.direction)
                            gestionnaire.etat.notifier()
                            self._envoyer(client, 'PASSAGE_AUTORISE')
                        elif commande == 'ETAT' and vehicule is not None:
                            couleur = gestionnaire.etat.etat_feu(vehicule.direction)
                            self._envoyer(client, f'FEU|{vehicule.direction}|{couleur}')
                        elif commande == 'TERMINE' and vehicule is not None:
                            if vehicule.progression != 100:
                                raise ValueError('Le client ne signale pas une sortie terminee')
                            with gestionnaire.etat.verrou:
                                gestionnaire.etat.enregistrer_passage(vehicule)
                                gestionnaire.etat.vehicules.pop(vehicule.nom, None)
                                gestionnaire.etat.revision += 1
                                if vehicule.prioritaire and gestionnaire.etat.priorite == vehicule.direction:
                                    gestionnaire.etat.changer_feux(None)
                            vehicule = None
                            gestionnaire.etat.notifier()
                            self._envoyer(client, 'OK')
                            break
                        else:
                            raise ValueError('Commande inconnue : mettre a jour les clients')
                    except (ValueError, KeyError, TypeError) as erreur:
                        self._envoyer(client, f'ERREUR|{erreur}')
        except (OSError, UnicodeError) as erreur:
            if not self.arret.is_set():
                print(f'Connexion fermee : {erreur}')
        finally:
            if vehicule is not None:
                with gestionnaire.etat.verrou:
                    gestionnaire.etat.vehicules.pop(vehicule.nom, None)
                    gestionnaire.etat.revision += 1
                    if vehicule.prioritaire and gestionnaire.etat.priorite == vehicule.direction:
                        gestionnaire.etat.changer_feux(None)
                gestionnaire.etat.notifier()

    def arreter(self):
        self.arret.set()
        if self.socket_serveur:
            try:
                self.socket_serveur.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.socket_serveur.close()
