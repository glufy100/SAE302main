from dataclasses import replace
import json
import socket
import threading
from server.config import BIND_HOST, DEBUT_CENTRE, DISTANCE_SORTIE, FIN_CENTRE, LIGNE_ARRET, PAS_AVANCEMENT, PAS_SIMULATION, PORT, POSITION_ATTENTE_GAUCHE, PAS_RANGEMENT_URGENCE, PAS_PREPARATION_DEPASSEMENT
from server.model.EtatCarrefour import EtatCarrefour
from server.model.Vehicule import Vehicule
from server.model.TrajectoireVehicule import TrajectoireVehicule


class ServeurCarrefour:
    """Serveur TCP qui recoit les vehicules."""

    def __init__(self, etat: EtatCarrefour, host: str = BIND_HOST, port: int = PORT, etat_t: EtatCarrefour | None = None):
        if not isinstance(etat, EtatCarrefour):
            raise TypeError("etat doit etre une instance de EtatCarrefour")
        if not isinstance(host, str):
            raise TypeError("host doit etre une chaine de caracteres")
        if not isinstance(port, int):
            raise TypeError("port doit etre un entier")
        self.etat = etat
        self.carrefours = {etat.type_carrefour: self}
        if etat_t is not None:
            if etat_t.type_carrefour != "T" or etat_t is etat:
                raise ValueError("etat_t doit etre un etat distinct de type T")
            self.carrefours["T"] = ServeurCarrefour(etat_t, host, port)
        self.host = host
        self.port = port
        self.socket_serveur = None
        self.arret = threading.Event()

    def demarrer(self):
        """Demarre le serveur TCP."""
        try:
            self.socket_serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_serveur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket_serveur.bind((self.host, self.port))
            self.port = self.socket_serveur.getsockname()[1]
            self.socket_serveur.listen()
            print(f"Serveur du carrefour en ecoute sur {self.host}:{self.port}")
            threading.Thread(target=self._accepter_clients, daemon=True).start()
        except OSError:
            if self.socket_serveur:
                self.socket_serveur.close()
            raise

    def _accepter_clients(self):
        """Accepte les connexions des voitures."""
        while not self.arret.is_set():
            try:
                client, _ = self.socket_serveur.accept()
                threading.Thread(target=self._gerer_client, args=(client,), daemon=True).start()
            except OSError:
                break

    def _envoyer(self, client: socket.socket, message: str):
        """Envoie une ligne de texte a un client."""
        client.sendall((message + "\n").encode("utf-8"))

    @staticmethod
    def _direction_a_droite(direction: str) -> str:
        return {"N": "E", "E": "S", "S": "O", "O": "N"}[direction]

    def _voie_sortie_occupee(self, vehicule: Vehicule, prochaine_position: int) -> bool:
        """Verifie la distance avec les voitures qui prennent la meme sortie."""
        if prochaine_position < DEBUT_CENTRE:
            return False

        for autre in self.etat.vehicules.values():
            if autre.nom == vehicule.nom or autre.progression >= 100:
                continue
            if autre.manoeuvre == "GAUCHE" and autre.progression <= POSITION_ATTENTE_GAUCHE:
                continue
            if autre.direction_sortie() != vehicule.direction_sortie():
                continue
            if (autre.progression >= DEBUT_CENTRE
                    and autre.progression > vehicule.progression
                    and prochaine_position > autre.progression - DISTANCE_SORTIE):
                return True
        return False

    def _attend_la_circulation_opposee(self, vehicule):
        """Un tourne-a-gauche cede aux vehicules venant en face au vert."""
        opposee = {"N": "S", "S": "N", "E": "O", "O": "E"}[vehicule.direction]
        return any(
            autre.direction == opposee
            and autre.manoeuvre != "GAUCHE"
            and LIGNE_ARRET <= autre.progression <= FIN_CENTRE
            and (autre.engagee or self.etat.feux[opposee] == "VERT")
            for autre in self.etat.vehicules.values()
        )

    def _ranger_pour_urgence(self, vehicule):
        """Range les voitures a droite puis les remet sur leur voie apres l'urgence.

        Appelee sous verrou. La progression reste fixe pendant cette manoeuvre,
        les demandes POSITION suivantes animent le decalage lateral.
        """
        if vehicule.prioritaire or vehicule.engagee:
            return False
        marge = self.etat.distance_securite(vehicule.direction)
        doit_laisser_passer = any(
            autre.prioritaire and autre.direction == vehicule.direction
            and autre.nom != vehicule.nom and autre.progression < 100
            and autre.progression < vehicule.progression + marge
            for autre in self.etat.vehicules.values()
        )
        if not doit_laisser_passer and vehicule.decalage_urgence == 0:
            vehicule.retour_voie = False
            return False
        if doit_laisser_passer:
            vehicule.retour_voie = False
        elif not vehicule.retour_voie:
            if TrajectoireVehicule.reinsertion_occupee(
                vehicule, self.etat.vehicules.values(), self.etat.geometries_affichage.values(),
            ):
                return True
            vehicule.retour_voie = True
        if doit_laisser_passer:
            decalage = min(1.0, round(vehicule.decalage_urgence + PAS_RANGEMENT_URGENCE, 2))
        else:
            decalage = max(0.0, round(vehicule.decalage_urgence - PAS_RANGEMENT_URGENCE, 2))
        if not TrajectoireVehicule.mouvement_occupe(
            vehicule, vehicule.progression, self.etat.vehicules.values(),
            self.etat.geometries_affichage.values(), decalage_urgence=decalage,
        ):
            vehicule.decalage_urgence = decalage
        return True

    def _preparer_depassement(self, vehicule, feu_vert):
        """Commence l'ecart pres de la ligne, apres l'engagement du tourne-a-gauche."""
        if (vehicule.prioritaire or vehicule.manoeuvre != "TOUT_DROIT"
                or vehicule.progression > LIGNE_ARRET or vehicule.decalage_urgence > 0):
            return False
        if not vehicule.depassement_droite:
            if not feu_vert or vehicule.progression < LIGNE_ARRET - self.etat.distance_securite(vehicule.direction):
                return False
            voiture_devant = min(
                (autre for autre in self.etat.vehicules.values()
                 if autre.nom != vehicule.nom and autre.direction == vehicule.direction
                 and autre.decalage_urgence < 1.0
                 and vehicule.progression < autre.progression < 100),
                key=lambda autre: autre.progression,
                default=None,
            )
            if (voiture_devant is None or voiture_devant.manoeuvre != "GAUCHE"
                    or voiture_devant.prioritaire or not voiture_devant.engagee
                    or not POSITION_ATTENTE_GAUCHE <= voiture_devant.progression <= FIN_CENTRE):
                return False
            vehicule.depassement_droite = True
            vehicule.preparation_depassement = 0.0
        if vehicule.preparation_depassement >= 1.0:
            return False
        # L'ecart se fait progressivement, a progression longitudinale fixe.
        # Un declenchement plus tardif ne provoque donc pas de saut de position.
        preparation = min(1.0, round(vehicule.preparation_depassement + PAS_PREPARATION_DEPASSEMENT, 2))
        proposition = replace(vehicule, preparation_depassement=preparation)
        if not TrajectoireVehicule.mouvement_occupe(
            proposition, vehicule.progression, self.etat.vehicules.values(),
            self.etat.geometries_affichage.values(),
        ):
            vehicule.preparation_depassement = preparation
        return True

    def _avancer_vehicule(self, client: socket.socket, vehicule: Vehicule, prochaine_position: int):
        """Accepte ou refuse le prochain pas propose par le vehicule."""
        if not isinstance(vehicule, Vehicule):
            raise TypeError("vehicule doit etre un Vehicule.")

        with self.etat.verrou:
            feu_vert = self.etat.feux[vehicule.direction] == "VERT"
            commence_le_virage = (vehicule.manoeuvre == "GAUCHE"
                                  and vehicule.progression <= POSITION_ATTENTE_GAUCHE < prochaine_position)
            entre_dans_le_carrefour = (not vehicule.engagee and prochaine_position > LIGNE_ARRET)
            doit_reserver = entre_dans_le_carrefour or commence_le_virage
            reponse = ""

            if not vehicule.progression < prochaine_position <= min(vehicule.progression + PAS_AVANCEMENT, 100):
                reponse = "ATTENTE"

            # Une demande immobile au rouge peut tout de meme animer le
            # rangement ou la reinsertion, sans franchir la ligne d'arret.
            if (not reponse or prochaine_position == vehicule.progression) and self._ranger_pour_urgence(vehicule):
                reponse = "ATTENTE"

            if not reponse and self._preparer_depassement(vehicule, feu_vert):
                reponse = "ATTENTE"

            if not reponse:
                voitures_devant = [
                    autre.progression
                    for autre in self.etat.vehicules.values()
                    if autre.nom != vehicule.nom
                    and autre.direction == vehicule.direction
                    and autre.decalage_urgence < 1.0
                    and not (autre.virage_gauche_entame() and vehicule.manoeuvre != "GAUCHE")
                    and vehicule.progression < autre.progression < 100
                ]

                if voitures_devant:
                    position_voiture_devant = min(voitures_devant)
                    distance_trop_courte = prochaine_position > position_voiture_devant - self.etat.distance_securite(vehicule.direction)
                    if distance_trop_courte:
                        reponse = "ATTENTE"

            if not vehicule.engagee and not reponse and not feu_vert:
                if vehicule.progression >= LIGNE_ARRET:
                    reponse = "ATTENTE"
                else:
                    # La ligne d'arret ne dispense pas du controle des contours.
                    # La position est appliquee uniquement apres tous les controles.
                    prochaine_position = min(prochaine_position, LIGNE_ARRET)
                    doit_reserver = prochaine_position > LIGNE_ARRET

            if not reponse and commence_le_virage and self._attend_la_circulation_opposee(vehicule):
                reponse = "ATTENTE"

            if not reponse and doit_reserver:
                carrefour_occupe = any(
                    autre.nom != vehicule.nom
                    and autre.direction != vehicule.direction
                    and autre.engagee
                    and autre.progression <= FIN_CENTRE
                    and TrajectoireVehicule.trajets_en_conflit(
                        replace(vehicule, progression=prochaine_position), autre,
                        self.etat.geometries_affichage.values())
                    for autre in self.etat.vehicules.values()
                )

                # Une voiture deja engagee doit pouvoir finir de degager
                # avant de ceder au nouveau vert d'une urgence.
                vehicule_prioritaire_a_droite = not vehicule.engagee and any(
                    autre.direction == self._direction_a_droite(vehicule.direction)
                    and not autre.engagee
                    and autre.progression >= LIGNE_ARRET
                    and self.etat.feux[autre.direction] == "VERT"
                    for autre in self.etat.vehicules.values()
                )

                carrefour_occupe = carrefour_occupe or vehicule_prioritaire_a_droite
                if carrefour_occupe:
                    reponse = "ATTENTE"

            if not reponse and self._voie_sortie_occupee(vehicule, prochaine_position):
                reponse = "ATTENTE"

            if not reponse and TrajectoireVehicule.mouvement_occupe(
                vehicule, prochaine_position, self.etat.vehicules.values(),
                self.etat.geometries_affichage.values(),
            ):
                reponse = "ATTENTE"

            if not reponse:
                vehicule.progression = prochaine_position
                if vehicule.progression > LIGNE_ARRET:
                    vehicule.engagee = True
                reponse = "OK"
            est_en_attente = reponse == "ATTENTE"

        if est_en_attente:
            self.etat.enregistrer_attente(vehicule, PAS_SIMULATION)

        self._envoyer(client, reponse)
        self.etat.notifier()

    def _gerer_client(self, client: socket.socket):
        """Traite les commandes envoyees par un client."""
        vehicule = None
        gestionnaire = self
        try:
            with client, client.makefile("r", encoding="utf-8") as lecteur:
                for ligne in lecteur:
                    morceaux = ligne.strip().split("|")
                    commande = morceaux[0]

                    if commande == "CARREFOUR":
                        selection = self.carrefours.get(morceaux[1])
                        if vehicule is not None or selection is None:
                            self._envoyer(client, "ERREUR|Carrefour indisponible ou vehicule deja inscrit")
                            continue
                        gestionnaire = selection
                        self._envoyer(client, "OK")

                    elif commande == "GET_TRAJETS":
                        self._envoyer(client, "TRAJETS|" + json.dumps(gestionnaire.etat.trajets))

                    elif commande == "GET_LIGNE_ARRET":
                        self._envoyer(client, str(LIGNE_ARRET))

                    elif commande == "GET_PAS_AVANCEMENT":
                        self._envoyer(client, str(PAS_AVANCEMENT))

                    elif commande == "GET_PAS_SIMULATION":
                        self._envoyer(client, str(PAS_SIMULATION))

                    elif commande == "IDENTITE":
                        if (vehicule is not None or morceaux[3] not in gestionnaire.etat.trajets
                                or morceaux[4] not in gestionnaire.etat.trajets[morceaux[3]]):
                            self._envoyer(client, "ERREUR|Trajet interdit pour ce carrefour")
                            continue
                        vehicule = gestionnaire._creer_vehicule(
                            morceaux[1],
                            morceaux[2],
                            morceaux[3],
                            morceaux[4],
                            int(morceaux[5])
                        )

                        if vehicule is None:
                            self._envoyer(client, "ATTENTE")
                            continue

                        self._envoyer(client, "OK")
                        gestionnaire.etat.notifier()

                    elif commande == "ETAT":
                        couleur = gestionnaire.etat.etat_feu(vehicule.direction)
                        self._envoyer(client, f"FEU|{vehicule.direction}|{couleur}")

                    elif commande == "URGENCE":
                        vehicule.prioritaire = True
                        gestionnaire.etat.changer_feux(vehicule.direction)
                        self._envoyer(client, "PASSAGE_AUTORISE")
                        gestionnaire.etat.notifier()

                    elif commande == "POSITION":
                        gestionnaire._avancer_vehicule(client, vehicule, int(morceaux[1]))

                    elif commande == "TERMINE":
                        gestionnaire.etat.enregistrer_passage(vehicule)

                        if vehicule.prioritaire:
                            gestionnaire.etat.changer_feux(None)
                            gestionnaire.etat.notifier()

        except Exception as erreur:
            print(f"Erreur avec un client : {erreur}")

        finally:
            if vehicule:
                with gestionnaire.etat.verrou:
                    etait_prioritaire = (
                        vehicule.prioritaire
                        and gestionnaire.etat.priorite == vehicule.direction
                    )

                    gestionnaire.etat.vehicules.pop(vehicule.nom, None)

                if etait_prioritaire:
                    gestionnaire.etat.changer_feux(None)

                gestionnaire.etat.notifier()

    def _creer_vehicule(self, nom: str, type_vehicule: str, direction: str, manoeuvre: str, position_depart: int) -> Vehicule | None:
        """Cree un vehicule et l'ajoute au carrefour."""
        if direction not in self.etat.trajets or manoeuvre not in self.etat.trajets[direction]:
            return None
        identifiant = self.etat.creer_identifiant_affichage()

        with self.etat.verrou:
            for autre in self.etat.vehicules.values():
                if autre.direction == direction and autre.progression < 100:
                    if autre.progression <= position_depart or position_depart > autre.progression - self.etat.distance_securite(direction):
                        return None

            vehicule = Vehicule(
                nom,
                type_vehicule,
                direction,
                identifiant,
                manoeuvre=manoeuvre,
                progression=position_depart,
            )

            self.etat.vehicules[vehicule.nom] = vehicule

        return vehicule

    def arreter(self):
        """Arrete le serveur."""
        self.arret.set()
        if self.socket_serveur:
            self.socket_serveur.close()
