import unittest
import coffre
from coffre import Coffre, Emetteur, Secret, fabriquer_secret


class TestSingleton(unittest.TestCase):
    def test_meme_objet(self):
        a = Emetteur()
        b = Emetteur()
        self.assertIs(a, b)


class TestFactory(unittest.TestCase):
    def test_quatrieme_genre_une_seule_ligne(self):
        class Certificat(Secret):
            def apercu(self):
                return "certificat : " + self._libelle()

        coffre._GENRES["certificat"] = Certificat
        try:
            self.assertIsInstance(
                fabriquer_secret("certificat", "1111111", "x", "v"), Certificat)
            c = Coffre(":memory:")
            c.creer_compte("1111111", "Abcdefgh1234", "consultant")
            s = c.ouvrir_session("1111111", "Abcdefgh1234")
            i = c.ajouter_secret(s, "certificat", "Mon certificat", "valeur")
            self.assertEqual(c.lister(s), [f"{i} | certificat : Mon certificat"])
            self.assertEqual(c.reveler(s, i), "valeur")
        finally:
            del coffre._GENRES["certificat"]

class TestObservateur(unittest.TestCase):
    def test_un_ecouteur_recoit_les_evenements(self):
        recus = []
        Emetteur().abonner(lambda nom, **d: recus.append(d["action"]))
        c = Coffre(":memory:")
    
        c.creer_compte("1111111", "Abcdefgh1234", "consultant")
        c.ouvrir_session("1111111", "Abcdefgh1234")
        self.assertIn("COMPTE_CREE", recus)
        self.assertIn("CONNEXION_OK", recus)
if __name__ == "__main__":
    unittest.main()