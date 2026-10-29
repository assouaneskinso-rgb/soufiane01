# Coffre-fort de secrets

Pour installer : `pip install cryptography`
Pour tester : `py test_patrons.py`

## Les 3 patrons

**Singleton** : Il n'y a qu'un seul `Emetteur`, pour que tous les événements passent par le même endroit : `Coffre` les envoie et `Journal` les écoute, donc les deux parlent forcément au même émetteur. S'il y en avait deux, `Journal` pourrait écouter un émetteur différent de celui de `Coffre` et ne recevrait rien.

**Factory** : fabriquer_secret crée l’objet selon le genre demandé et renvoie le bon type de secret.

**Observer** : Coffre n’écrit pas lui-même dans audit : il annonce seulement ce qui se passe, et Journal s’occupe de l’enregistrer. Chacun a sa responsabilité. On peut ajouter plusieurs écouteurs sans modifier Coffre, ce qui rend le programme facile à faire évoluer.

## Ajouter un 4e genre de secret

Pour ajouter un 4e genre, il faut créer une nouvelle classe et l’enregistrer dans _GENRES, sans modifier ajouter_secret, lister ni reveler.

On modifie **1 ligne** : celle de `_GENRES` dans `coffre.py`.
(Plus la nouvelle classe, qui est du code nouveau.)

## Questions de réflexion (partie D)

**1. Le mot de passe maître et la valeur d'un secret ne sont pas protégés pareil**

Le mot de passe maître est protégé avec scrypt : on s’en sert seulement pour vérifier le mot de passe tapé, et on ne peut jamais le retrouver à partir du hachage.

La valeur d’un secret est protégée avec Fernet : on la chiffre, puis on la déchiffre, car son propriétaire doit pouvoir la relire plus tard.

**2. Méthode retenue, et ce qu'un attaquant obtient avec le fichier seul**

Les mots de passe sont stockés sous forme de hachage scrypt, et les valeurs des secrets sont chiffrées avec Fernet. La clé n’est pas dans la base de données. Avec le fichier seul, l’attaquant ne peut donc pas lire les secrets, car il n’a pas la clé.

## Lancement

Installer le module de chiffrement :

    py -m pip install cryptography

Lancer les tests :

    py test_patrons.py

Lancer le menu console :

    py menu_console.py

Lancer la fenêtre :

    py fenetre.py

    ## Usage de l'IA

J’ai utilisé Claude, développé par Anthropic, lorsque je pensais avoir fait des erreurs ou lorsque je ne comprenais pas certaines parties du code. Je lui ai demandé des explications pour mieux comprendre le fonctionnement du programme et de l’aide pour trouver et corriger les erreurs. J’ai réalisé moi-même le diagramme sur papier, le journal de débogage et les justifications de mes choix. Cette aide m’a permis de mieux comprendre le code et d’apprendre de mes erreurs.