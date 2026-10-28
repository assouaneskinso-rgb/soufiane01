import getpass
import os

from coffre import Coffre, ErreurCoffre

CHEMIN_BD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coffre.db")

MENU = """
=== Coffre-fort ===
1. Créer un compte
2. Ouvrir une session
3. Ajouter un secret
4. Lister mes secrets
5. Révéler un secret
6. Consulter le journal
0. Quitter
"""


def creer_compte(coffre, etat):
    matricule = input("Matricule : ")
    mdp = getpass.getpass("Mot de passe maître : ")
    role = input("Rôle (consultant ou responsable) : ")
    coffre.creer_compte(matricule, mdp, role)
    print("Compte créé.")


def ouvrir_session(coffre, etat):
    matricule = input("Matricule : ")
    mdp = getpass.getpass("Mot de passe maître : ")
    etat["session"] = coffre.ouvrir_session(matricule, mdp)
    print("Session ouverte.")


def ajouter_secret(coffre, etat):
    genre = input("Genre (motdepasse, cleapi ou note) : ")
    libelle = input("Libellé : ")
    valeur = getpass.getpass("Valeur : ")
    identifiant = coffre.ajouter_secret(etat["session"], genre, libelle, valeur)
    print(f"Secret ajouté (id {identifiant}).")


def lister(coffre, etat):
    lignes = coffre.lister(etat["session"])
    if not lignes:
        print("Aucun secret.")
    for ligne in lignes:
        print(ligne)


def reveler(coffre, etat):
    try:
        identifiant = int(input("Identifiant du secret : "))
    except ValueError:
        print("Erreur : l'identifiant doit être un nombre entier.")
        return
    print("Valeur :", coffre.reveler(etat["session"], identifiant))


def journal(coffre, etat):
    for ligne in coffre.journal(etat["session"]):
        print(ligne)


ACTIONS = {
    "1": creer_compte,
    "2": ouvrir_session,
    "3": ajouter_secret,
    "4": lister,
    "5": reveler,
    "6": journal,
}


def main():
    coffre = Coffre(CHEMIN_BD)
    etat = {"session": None}
    try:
        while True:
            print(MENU)
            try:
                choix = input("Votre choix : ").strip()
            except EOFError:
                break
            if choix == "0":
                break
            action = ACTIONS.get(choix)
            if action is None:
                print("Choix invalide : tapez un nombre de 0 à 6.")
                continue
            try:
                action(coffre, etat)
            except ErreurCoffre as erreur:
                print("Erreur :", erreur)
            except EOFError:
                break
    finally:
        coffre.fermer()
        print("Au revoir.")


if __name__ == "__main__":
    main()