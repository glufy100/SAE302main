"""Decisions de chaque vehicule, executees exclusivement par son client."""

from dataclasses import replace

if __package__:
    from .config import (DEBUT_CENTRE, DISTANCE_SORTIE, FIN_CENTRE, LIGNE_ARRET,
                         PAS_AVANCEMENT, PAS_SIMULATION, POSITION_ATTENTE_GAUCHE,
                         PAS_RANGEMENT_URGENCE, PAS_PREPARATION_DEPASSEMENT)
    from .trajectoire import TrajectoireVehicule
    from .vehicule import Vehicule
else:
    from config import (DEBUT_CENTRE, DISTANCE_SORTIE, FIN_CENTRE, LIGNE_ARRET,
                        PAS_AVANCEMENT, PAS_SIMULATION, POSITION_ATTENTE_GAUCHE,
                        PAS_RANGEMENT_URGENCE, PAS_PREPARATION_DEPASSEMENT)
    from trajectoire import TrajectoireVehicule
    from vehicule import Vehicule


class Perception:
    """Copie locale de l'etat du trafic recu par TCP."""

    def __init__(self, instantane):
        self.feux = dict(instantane['feux'])
        self.vehicules = {donnees['nom']: Vehicule(**donnees) for donnees in instantane['vehicules']}
        geometrie, haut = instantane['scene']
        geometrie = tuple(geometrie)
        self.geometries_affichage = {'scene': (geometrie, haut)}
        self.distances = TrajectoireVehicule._distances_securite(geometrie, haut)

    def distance_securite(self, direction):
        return self.distances[direction]


class ConduiteVehicule:
    def __init__(self, perception):
        self.etat = perception

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

        La progression reste fixe pendant cette manoeuvre,
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

    def calculer(self, vehicule: Vehicule, prochaine_position: int | None = None):
        """Calcule localement le prochain etat et la pose graphique de cette voiture."""
        if not isinstance(vehicule, Vehicule):
            raise TypeError("vehicule doit etre un Vehicule.")

        vehicule = replace(vehicule)
        self.etat.vehicules[vehicule.nom] = vehicule
        if prochaine_position is None:
            prochaine_position = min(100, vehicule.progression + PAS_AVANCEMENT)
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
            # Le refuge libere la voie pour l'urgence seulement. Les voitures
            # normales restent dans la file pour laisser la reinsertion possible.
            voitures_devant = [
                autre.progression
                for autre in self.etat.vehicules.values()
                if autre.nom != vehicule.nom
                and autre.direction == vehicule.direction
                and (autre.decalage_urgence < 1.0 or not vehicule.prioritaire)
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
            vehicule.temps_attente += PAS_SIMULATION
        actualiser_affichage(vehicule, self.etat)
        return vehicule, est_en_attente


def actualiser_affichage(vehicule, perception):
    """Le client produit aussi les coordonnees et l'orientation a dessiner."""
    vehicule.dans_carrefour = vehicule.engagee and vehicule.progression <= FIN_CENTRE
    geometrie, haut = next(iter(perception.geometries_affichage.values()))
    position = TrajectoireVehicule._position_vehicule(vehicule, *geometrie, haut)
    if position is None:
        raise ValueError('Trajet absent de ce carrefour')
    centre, angle, longueur, largeur = position
    vehicule.position_affichage = (centre.x(), centre.y(), angle, longueur, largeur)


def proposer_arrivee(nom, type_vehicule, direction, manoeuvre, instantane):
    if direction not in instantane['trajets'] or manoeuvre not in instantane['trajets'][direction]:
        raise ValueError('Trajet interdit pour ce carrefour')
    perception = Perception(instantane)
    distance = perception.distance_securite(direction)
    position = min([0] + [v.progression - distance for v in perception.vehicules.values()
                          if v.direction == direction and v.progression < 100])
    vehicule = Vehicule(nom, type_vehicule, direction, '', manoeuvre=manoeuvre, progression=position)
    if not position_depart_libre(vehicule, perception):
        raise ValueError('Aucune place de depart trouvee dans cet instantane')
    actualiser_affichage(vehicule, perception)
    return vehicule


def position_depart_libre(vehicule, perception):
    distance = perception.distance_securite(vehicule.direction)
    return all(autre.progression > vehicule.progression
               and vehicule.progression <= autre.progression - distance
               for autre in perception.vehicules.values()
               if autre.nom != vehicule.nom and autre.direction == vehicule.direction
               and autre.progression < 100)
