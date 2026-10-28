# Journal de débogage

## Erreur 1 : commande collée dans le mauvais fichier

**Symptôme :** La première ligne de `fenetre.py` contenait plusieurs commandes `copy` collées juste avant `import os`, tout était souligné en rouge et le compteur affichait 14 problèmes.

**Comment je l'ai localisée :** J’ai regardé la première ligne du fichier, les soulignements rouges et le compteur « Problems » pour repérer l’erreur.

**Cause :** J’avais collé les commandes `copy` dans l’éditeur au lieu du terminal, car le curseur était resté dans le fichier `fenetre.py`.

**Correction :** J’ai supprimé la ligne incorrecte, mais `import os` a disparu aussi, laissant la ligne `os.path…` en rouge. J’ai réécrit `import os` et enregistré avec `Ctrl + S`, ce qui a fait disparaître le rouge. Pour éviter que cela se reproduise, je cliquerai dans le terminal avant de coller une commande.

## Erreur 2 : fichier non enregistré (le test ne recevait rien)

**Symptôme :** Le test `TestObservateur` indiquait que la liste `recus` était vide, alors qu’elle aurait dû contenir les messages reçus.

**Comment je l'ai localisée :** J’ai regardé le résultat du test et remarqué le point blanc dans l’onglet de `coffre.py`, qui indiquait que le fichier n’était pas enregistré.

**Cause :** J’avais ajouté les classes `Emetteur` et `Journal` dans `coffre.py`, mais j’avais oublié d’enregistrer le fichier, donc Python utilisait encore l’ancienne version du code.

**Correction :** J’ai enregistré `coffre.py` avec `Ctrl + S`, puis j’ai relancé le test, qui a réussi avec le résultat « Ran 3 tests … OK ».