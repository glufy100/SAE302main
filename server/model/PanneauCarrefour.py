from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from server.model.EtatCarrefour import EtatCarrefour


class PanneauCarrefour(QWidget):
    """Associe une vue aux compteurs communs aux deux carrefours."""

    def __init__(self, etat: EtatCarrefour, vue):
        super().__init__()
        self.etat = etat
        self.vue = vue
        self.connexions_label = QLabel()
        self.stats_label = QLabel()
        disposition = QVBoxLayout(self)
        disposition.addWidget(self.vue, stretch=1)
        disposition.addWidget(self.connexions_label)
        disposition.addWidget(self.stats_label)
        etat.change.connect(self.actualiser)
        self.actualiser()

    def actualiser(self):
        """Rafraichit les compteurs puis demande le nouveau dessin."""
        with self.etat.verrou:
            nombre = len(self.etat.vehicules)
            passages = self.etat.passages_termines
            urgences = self.etat.urgences_traitees
            attente = self.etat.temps_attente_total
        self.connexions_label.setText(f"Vehicules connectes : {nombre}")
        self.stats_label.setText(
            f"Passages termines : {passages} | Urgences : {urgences} | "
            f"Attente totale : {attente:.1f}s"
        )
        self.vue.update()
