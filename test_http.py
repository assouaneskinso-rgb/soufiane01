import json
import threading
import unittest
import urllib.error
import urllib.request

import serveur

MDP = "Abcdefgh1234"


class TestHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = serveur.creer_serveur(":memory:", 0)
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def req(self, m, chemin, corps=None, jeton=None):
        r = urllib.request.Request(self.base + chemin, method=m,
                                   data=None if corps is None else json.dumps(corps).encode())
        if jeton:
            r.add_header("Authorization", "Bearer " + jeton)
        try:
            with urllib.request.urlopen(r) as x:
                b = x.read()
                return x.status, (json.loads(b) if b else None), x.headers
        except urllib.error.HTTPError as e:
            b = e.read()
            return e.code, (json.loads(b) if b else None), e.headers

    def compte(self, mat, role="consultant"):
        self.req("POST", "/comptes", {"matricule": mat, "mot_de_passe": MDP, "role": role})
        return self.req("POST", "/sessions", {"matricule": mat, "mot_de_passe": MDP})[1]["jeton"]

    def test_parcours(self):
        self.assertEqual(self.req("GET", "/sante")[0], 200)
        code, _, h = self.req("POST", "/comptes", {"matricule": "2000001", "mot_de_passe": MDP, "role": "consultant"})
        self.assertEqual((code, h["Location"]), (201, "/comptes/2000001"))
        self.assertEqual(self.req("POST", "/comptes", {"matricule": "2000001", "mot_de_passe": MDP, "role": "consultant"})[0], 409)
        self.assertEqual(self.req("POST", "/comptes", {"matricule": "x", "mot_de_passe": MDP, "role": "consultant"})[0], 422)
        self.assertEqual(self.req("POST", "/sessions", {"matricule": "2000001", "mot_de_passe": "Mauvais123456"})[0], 401)
        t = self.req("POST", "/sessions", {"matricule": "2000001", "mot_de_passe": MDP})[1]["jeton"]
        code, _, h = self.req("POST", "/secrets", {"genre": "note", "libelle": "b", "valeur": "v1"}, t)
        self.assertEqual(code, 201)
        loc = h["Location"]
        self.req("POST", "/secrets", {"genre": "cleapi", "libelle": "a", "valeur": "v2"}, t)
        self.assertEqual(self.req("POST", "/secrets", {"genre": "zzz", "libelle": "a", "valeur": "v"}, t)[0], 422)
        self.assertEqual(self.req("POST", "/secrets", {"genre": "note", "libelle": "a", "valeur": "v"})[0], 401)
        code, d, _ = self.req("GET", "/secrets?tri=libelle", jeton=t)
        self.assertEqual([x["libelle"] for x in d["secrets"]], ["a", "b"])
        self.assertNotIn("valeur", json.dumps(d))
        self.assertEqual(len(self.req("GET", "/secrets?genre=note", jeton=t)[1]["secrets"]), 1)
        self.assertEqual(len(self.req("GET", "/secrets?taille=1&page=2", jeton=t)[1]["secrets"]), 1)
        for q in ("genre=x", "tri=x", "page=0", "page=a", "taille=0", "taille=101", "foo=1"):
            self.assertEqual(self.req("GET", "/secrets?" + q, jeton=t)[0], 422, q)
        self.assertEqual(self.req("GET", "/secrets")[0], 401)
        code, d, _ = self.req("GET", loc, jeton=t)
        self.assertEqual(code, 200)
        self.assertNotIn("valeur", d)
        code, d, h = self.req("GET", loc + "/valeur", jeton=t)
        self.assertEqual((code, d["valeur"], h["Cache-Control"]), (200, "v1", "no-store"))
        t2 = self.compte("2000002")
        self.assertEqual(self.req("GET", loc, jeton=t2)[0], 403)
        self.assertEqual(self.req("GET", loc + "/valeur", jeton=t2)[0], 403)
        self.assertEqual(self.req("DELETE", loc, jeton=t2)[0], 403)
        self.assertEqual(self.req("GET", "/secrets/999", jeton=t)[0], 404)
        self.assertEqual(self.req("GET", loc + "/valeur")[0], 401)
        self.assertEqual(self.req("DELETE", loc, jeton=t)[0], 204)
        self.assertEqual(self.req("GET", loc, jeton=t)[0], 404)

    def test_journal_et_blocage(self):
        t = self.compte("3000001")
        r = self.compte("3000002", "responsable")
        self.assertEqual(self.req("GET", "/journal", jeton=t)[0], 403)
        self.assertEqual(self.req("GET", "/journal")[0], 401)
        self.assertEqual(self.req("GET", "/journal", jeton=r)[0], 200)
        code, d, _ = self.req("GET", "/journal?resume=1", jeton=r)
        self.assertEqual(code, 200)
        self.assertIn("par_action", d)
        self.assertEqual(self.req("GET", "/journal?resume=2", jeton=r)[0], 422)
        for _ in range(3):
            self.req("POST", "/sessions", {"matricule": "3000001", "mot_de_passe": "Mauvais123456"})
        self.assertEqual(self.req("POST", "/sessions", {"matricule": "3000001", "mot_de_passe": MDP})[0], 423)


if __name__ == "__main__":
    unittest.main()
