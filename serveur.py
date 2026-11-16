"""Serveur HTTP du coffre (TP2, étape 3). Lancer : py serveur.py [port]"""
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

from coffre import (AccesRefuse, AuthentificationEchouee, Coffre, CompteBloque,
                    CompteExistant, DonneeInvalide, SecretIntrouvable)

TAILLE_CORPS_MAX = 64 * 1024


class Reponse(Exception):
    def __init__(self, code, corps=None, entetes=None):
        self.code, self.corps, self.entetes = code, corps, entetes or {}


def _erreur(code, message, entetes=None):
    return Reponse(code, {"erreur": message}, entetes)


def _entier(texte, nom):
    if not re.fullmatch(r"[0-9]{1,9}", texte):
        raise _erreur(422, f"{nom} : entier invalide.")
    return int(texte)


def _verifier_params(params, autorises):
    for nom, valeurs in params.items():
        if nom not in autorises:
            raise _erreur(422, f"Paramètre inconnu : {nom}.")
        if len(valeurs) != 1:
            raise _erreur(422, f"Paramètre répété : {nom}.")
    return {n: v[0] for n, v in params.items()}


class Gestionnaire(BaseHTTPRequestHandler):
    coffre = None
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    # --- entrée ---
    def _jeton(self):
        h = self.headers.get("Authorization", "")
        m = re.fullmatch(r"Bearer (\S+)", h)
        return m.group(1) if m else None

    def _corps_json(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise _erreur(422, "Content-Length invalide.")
        if n > TAILLE_CORPS_MAX:
            raise _erreur(413, "Corps trop gros.")
        brut = self.rfile.read(n)
        try:
            d = json.loads(brut.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise _erreur(422, "JSON invalide.")
        if not isinstance(d, dict):
            raise _erreur(422, "Un objet JSON est attendu.")
        return d

    # --- routes ---
    def _router(self, methode):
        url = urlsplit(self.path)
        chemin, params = url.path, parse_qs(url.query, keep_blank_values=True)
        routes = [
            ("GET", r"/sante", self._sante, False),
            ("POST", r"/comptes", self._creer_compte, False),
            ("POST", r"/sessions", self._ouvrir_session, False),
            ("GET", r"/secrets", self._lister, True),
            ("POST", r"/secrets", self._ajouter, True),
            ("GET", r"/secrets/([^/]+)", self._metadonnees, True),
            ("GET", r"/secrets/([^/]+)/valeur", self._valeur, True),
            ("DELETE", r"/secrets/([^/]+)", self._supprimer, True),
            ("GET", r"/journal", self._journal, True),
        ]
        chemin_ok = False
        for m, motif, fn, auth in routes:
            ident = re.fullmatch(motif, chemin)
            if not ident:
                continue
            chemin_ok = True
            if m != methode:
                continue
            return fn, auth, ident.groups(), params
        if chemin_ok:
            raise _erreur(405, "Méthode non permise.")
        raise _erreur(404, "Route inconnue.")

    def _sante(self, **_):
        return Reponse(200, {"statut": "ok"})

    def _creer_compte(self, **_):
        d = self._corps_json()
        try:
            self.coffre.creer_compte(d.get("matricule"), d.get("mot_de_passe"),
                                     d.get("role"))
        except CompteExistant:
            raise _erreur(409, "Ce matricule existe déjà.")
        except DonneeInvalide as e:
            raise _erreur(422, str(e))
        return Reponse(201, {"matricule": d["matricule"]},
                       {"Location": "/comptes/" + d["matricule"]})

    def _ouvrir_session(self, **_):
        d = self._corps_json()
        try:
            jeton = self.coffre.ouvrir_session(d.get("matricule"),
                                               d.get("mot_de_passe"))
        except CompteBloque:
            raise _erreur(423, "Compte bloqué.")
        except AuthentificationEchouee:
            raise _erreur(401, "Identifiants invalides.",
                          {"WWW-Authenticate": "Bearer"})
        except DonneeInvalide:
            # Un matricule/mot de passe mal formé = mêmes réponse qu'un mauvais
            # identifiant (évite de révéler quoi que ce soit).
            raise _erreur(401, "Identifiants invalides.",
                          {"WWW-Authenticate": "Bearer"})
        return Reponse(201, {"jeton": jeton})

    def _lister(self, jeton, params, **_):
        p = _verifier_params(params, {"genre", "tri", "page", "taille"})
        self.coffre.lister(jeton)  # 401 d'abord, avant toute validation
        try:
            page = _entier(p["page"], "page") if "page" in p else 1
            taille = _entier(p["taille"], "taille") if "taille" in p else 20
            return Reponse(200, self.coffre.lister_meta(
                jeton, p.get("genre"), p.get("tri", "date"), page, taille))
        except DonneeInvalide as e:
            raise _erreur(422, str(e))

    def _ajouter(self, jeton, **_):
        self.coffre.lister(jeton)  # 401 d'abord
        d = self._corps_json()
        try:
            i = self.coffre.ajouter_secret(jeton, d.get("genre"),
                                           d.get("libelle"), d.get("valeur"))
        except DonneeInvalide as e:
            raise _erreur(422, str(e))
        return Reponse(201, {"id": i}, {"Location": f"/secrets/{i}"})

    @staticmethod
    def _id(texte):
        return int(texte) if re.fullmatch(r"[0-9]{1,9}", texte) else None

    def _metadonnees(self, jeton, ids, **_):
        return Reponse(200, self.coffre.metadonnees(jeton, self._id(ids[0])))

    def _valeur(self, jeton, ids, **_):
        v = self.coffre.valeur(jeton, self._id(ids[0]))
        return Reponse(200, {"valeur": v}, {"Cache-Control": "no-store"})

    def _supprimer(self, jeton, ids, **_):
        self.coffre.supprimer(jeton, self._id(ids[0]))
        return Reponse(204)

    def _journal(self, jeton, params, **_):
        p = _verifier_params(params, {"resume"})
        if p.get("resume", "0") not in ("0", "1"):
            self.coffre.lister(jeton)
            raise _erreur(422, "resume : 1 pour le résumé agrégé.")
        if p.get("resume") == "1":
            return Reponse(200, self.coffre.resume_journal(jeton))
        return Reponse(200, {"journal": self.coffre.journal(jeton)})

    # --- boucle commune ---
    def _traiter(self, methode):
        try:
            fn, auth, ids, params = self._router(methode)
            kw = {"ids": ids, "params": params}
            if auth:
                jeton = self._jeton()
                if jeton is None:
                    self.coffre.lister("")  # journalise la session invalide
                kw["jeton"] = jeton
            rep = fn(**kw)
        except Reponse as r:
            rep = r
        except SecretIntrouvable:
            rep = _erreur(404, "Introuvable.")
        except AccesRefuse as e:
            # Jeton inconnu => 401 ; secret d'autrui / rôle insuffisant => 403
            rep = (_erreur(401, "Authentification requise.", {"WWW-Authenticate": "Bearer"})
                   if self._jeton_invalide() else _erreur(403, "Accès refusé."))
        self._envoyer(rep)

    def _jeton_invalide(self):
        return not self.coffre.session_valide(self._jeton())

    def _envoyer(self, rep):
        corps = b"" if rep.corps is None else json.dumps(
            rep.corps, ensure_ascii=False).encode("utf-8")
        self.send_response(rep.code)
        if rep.corps is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        for k, v in rep.entetes.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        if corps:
            self.wfile.write(corps)

    def do_GET(self): self._traiter("GET")
    def do_POST(self): self._traiter("POST")
    def do_DELETE(self): self._traiter("DELETE")


def creer_serveur(chemin_bd="coffre.db", port=8000):
    Gestionnaire.coffre = Coffre(chemin_bd)
    return HTTPServer(("127.0.0.1", port), Gestionnaire)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Coffre sur http://127.0.0.1:{port}")
    creer_serveur(port=port).serve_forever()
