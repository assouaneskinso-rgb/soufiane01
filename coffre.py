import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from cryptography.fernet import Fernet
class ErreurCoffre(Exception):
    pass
class AuthentificationEchouee(ErreurCoffre):
    pass
class AccesRefuse(ErreurCoffre):
    pass
class DonneeInvalide(ErreurCoffre):
    pass
class Secret(ABC):
    def __init__(self, proprietaire, libelle, valeur):
        self.__proprietaire = proprietaire
        self.__libelle = libelle
        self.__valeur = valeur
    def appartient_a(self, matricule):
        return self.__proprietaire == matricule
    def _libelle(self):
        return self.__libelle
    def reveler(self):
        return self.__valeur
    @abstractmethod
    def apercu(self):
        ...
class MotDePasse(Secret):
    def apercu(self):
        return "mot de passe : " + self._libelle()
class CleApi(Secret):
    def apercu(self):
        return "clé d'API : " + self._libelle()
class Note(Secret):
    def apercu(self):
        return "note : " + self._libelle()
_GENRES = {"motdepasse": MotDePasse, "cleapi": CleApi, "note": Note}

def fabriquer_secret(genre, proprietaire, libelle, valeur):
    return _GENRES[genre](proprietaire, libelle, valeur)
class Session:
    def __init__(self, matricule, role, cle):
        self.__matricule = matricule
        self.__role = role
        self.__fernet = Fernet(base64.urlsafe_b64encode(cle))
    @property
    def matricule(self):
        return self.__matricule
    @property
    def role(self):
        return self.__role
    def chiffrer(self, texte):
        return self.__fernet.encrypt(texte.encode())
    def dechiffrer(self, jeton):
        return self.__fernet.decrypt(jeton).decode()
class Emetteur:
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.__ecouteurs = []
        return cls.__instance

    def abonner(self, fonction):
        self.__ecouteurs.append(fonction)

    def emettre(self, nom, **donnees):
        for fonction in self.__ecouteurs:
            fonction(nom, **donnees)
_SEL_BIDON = bytes(16)
_EMPREINTE_BIDON = bytes(32)
class Coffre:
    def __init__(self, chemin_bd):
        self.__bd = sqlite3.connect(str(chemin_bd))
        self.__bd.execute("""
            CREATE TABLE IF NOT EXISTS compte (
                matricule TEXT PRIMARY KEY,
                role      TEXT NOT NULL,
                sel       BLOB NOT NULL,
                empreinte BLOB NOT NULL,
                echecs    INTEGER NOT NULL DEFAULT 0)""")
        self.__bd.execute("""
            CREATE TABLE IF NOT EXISTS secret (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                proprietaire TEXT NOT NULL REFERENCES compte(matricule),
                genre        TEXT NOT NULL,
                libelle      TEXT NOT NULL,
                valeur_chiffree BLOB NOT NULL)""")
        self.__bd.execute("""
            CREATE TABLE IF NOT EXISTS audit (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                quand   TEXT NOT NULL,
                acteur  TEXT,
                action  TEXT NOT NULL,
                detail  TEXT NOT NULL DEFAULT '')""")
        self.__bd.commit()
        self.__sessions = {}
    def creer_compte(self, matricule, mdp_maitre, role):
        if not (isinstance(matricule, str) and re.fullmatch(r"[0-9]{7}", matricule)):
            raise DonneeInvalide("Matricule : 7 chiffres.")
        if not (isinstance(mdp_maitre, str) and len(mdp_maitre) >= 12
                and any(c.isupper() for c in mdp_maitre)
                and any(c.islower() for c in mdp_maitre)
                and any(c in "0123456789" for c in mdp_maitre)):
            raise DonneeInvalide("Mot de passe : 12 car. min., majuscule, "
                                 "minuscule et chiffre.")
        if role not in ("consultant", "responsable"):
            raise DonneeInvalide("Rôle : consultant ou responsable.")
        sel = os.urandom(16)
        empreinte = hashlib.scrypt(mdp_maitre.encode(), salt=sel,
                                   n=2**14, r=8, p=1, dklen=32)
        try:
            self.__bd.execute(
                "INSERT INTO compte (matricule, role, sel, empreinte)"
                " VALUES (?, ?, ?, ?)", (matricule, role, sel, empreinte))
            self.__bd.commit()
        except sqlite3.IntegrityError:
            raise DonneeInvalide("Ce matricule existe déjà.")
        self.__noter(matricule, "COMPTE_CREE", "role=" + role)
    def ouvrir_session(self, matricule, mdp_maitre):
        if not (isinstance(matricule, str) and re.fullmatch(r"[0-9]{7}", matricule)):
            raise DonneeInvalide("Matricule : 7 chiffres.")
        if not isinstance(mdp_maitre, str):
            raise DonneeInvalide("Mot de passe : texte.")
        ligne = self.__bd.execute(
            "SELECT role, sel, empreinte, echecs FROM compte WHERE matricule = ?",
            (matricule,)).fetchone()
        existe = ligne is not None
        role, sel, empreinte, echecs = ligne if existe else (None, _SEL_BIDON, _EMPREINTE_BIDON, 0)
        essai = hashlib.scrypt(mdp_maitre.encode(), salt=sel,
                               n=2**14, r=8, p=1, dklen=32)
        bon = hmac.compare_digest(essai, empreinte) and existe
        if existe and echecs >= 3:
            self.__noter(matricule, "CONNEXION_REFUSEE", "compte bloqué")
            raise AuthentificationEchouee("Identifiants invalides.")
        if not bon:
            if existe:
                self.__bd.execute(
                    "UPDATE compte SET echecs = echecs + 1 WHERE matricule = ?",
                    (matricule,))
                self.__bd.commit()
            self.__noter(matricule, "CONNEXION_ECHEC", "identifiants")
            if existe and echecs + 1 >= 3:
                self.__noter(matricule, "COMPTE_BLOQUE", "3 échecs consécutifs")
            raise AuthentificationEchouee("Identifiants invalides.")
        self.__bd.execute(
            "UPDATE compte SET echecs = 0 WHERE matricule = ?", (matricule,))
        self.__bd.commit()
        jeton = secrets.token_urlsafe(32)
        cle = hashlib.scrypt(mdp_maitre.encode(), salt=sel + b"cle",
                             n=2**14, r=8, p=1, dklen=32)
        self.__sessions[jeton] = Session(matricule, role, cle)
        self.__noter(matricule, "CONNEXION_OK")
        return jeton
    def ajouter_secret(self, session, genre, libelle, valeur):
        s = self.__session(session)
        if genre not in _GENRES:
            raise DonneeInvalide("Genre : motdepasse, cleapi ou note.")
        if not (isinstance(libelle, str) and 1 <= len(libelle) <= 60
                and libelle.strip()):
            raise DonneeInvalide("Libellé : 1 à 60 caractères, non vide.")
        if not isinstance(valeur, str) or valeur == "":
            raise DonneeInvalide("Valeur : texte non vide.")
        cur = self.__bd.execute(
            "INSERT INTO secret (proprietaire, genre, libelle, valeur_chiffree)"
            " VALUES (?, ?, ?, ?)",
            (s.matricule, genre, libelle, s.chiffrer(valeur)))
        self.__bd.commit()
        self.__noter(s.matricule, "SECRET_AJOUTE", f"id={cur.lastrowid} genre={genre}")
        return cur.lastrowid
    def lister(self, session):
        s = self.__session(session)
        lignes = self.__bd.execute(
            "SELECT id, genre, libelle FROM secret WHERE proprietaire = ?"
            " ORDER BY id", (s.matricule,)).fetchall()
        return [f"{i} | " + fabriquer_secret(g, s.matricule, lib, None).apercu()
                for i, g, lib in lignes]
    def reveler(self, session, id_secret):
        s = self.__session(session)
        if isinstance(id_secret, bool) or not isinstance(id_secret, int):
            raise DonneeInvalide("Identifiant : entier.")
        ligne = self.__bd.execute(
            "SELECT proprietaire, genre, libelle, valeur_chiffree"
            " FROM secret WHERE id = ?", (id_secret,)).fetchone()
        if ligne is None:
            self.__noter(s.matricule, "ACCES_REFUSE", f"reveler id={id_secret}")
            raise AccesRefuse("Accès refusé.")
        proprietaire, genre, libelle, chiffre = ligne
        secret = fabriquer_secret(genre, proprietaire, libelle,
                          s.dechiffrer(chiffre)
                          if proprietaire == s.matricule else None)
        if not secret.appartient_a(s.matricule):
            self.__noter(s.matricule, "ACCES_REFUSE", f"reveler id={id_secret}")
            raise AccesRefuse("Accès refusé.")
        self.__noter(s.matricule, "SECRET_REVELE", f"id={id_secret}")
        return secret.reveler()
    def journal(self, session):
        s = self.__session(session)
        if s.role != "responsable":
            self.__noter(s.matricule, "ACCES_REFUSE", "journal")
            raise AccesRefuse("Accès refusé.")
        lignes = self.__bd.execute(
            "SELECT quand, acteur, action, detail FROM audit ORDER BY id"
        ).fetchall()
        self.__noter(s.matricule, "JOURNAL_CONSULTE")
        return [f"{q} | {a or '-'} | {act} | {d}" for q, a, act, d in lignes]
    def fermer(self):
        self.__bd.close()
    def __noter(self, acteur, action, detail=""):
        Emetteur().emettre("evenement", bd=self.__bd,
                           acteur=acteur, action=action, detail=detail)

    def __session(self, jeton):
        s = self.__sessions.get(jeton) if isinstance(jeton, str) else None
        if s is None:
            self.__noter(None, "ACCES_REFUSE", "session invalide")
            raise AccesRefuse("Accès refusé.")
        return s
class Journal:
    def ecouter(self, nom, bd, acteur, action, detail):
        bd.execute(
            "INSERT INTO audit (quand, acteur, action, detail) VALUES (?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"),
             acteur, action, detail))
        bd.commit()


Emetteur().abonner(Journal().ecouter)