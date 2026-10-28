import os
import tkinter as tk

from coffre import Coffre, ErreurCoffre

CHEMIN_BD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coffre.db")


class Fenetre:
    def __init__(self, racine, coffre):
        self.racine = racine
        self.coffre = coffre
        self.session = None
        racine.title("Coffre-fort")
        racine.protocol("WM_DELETE_WINDOW", self.quitter)

        cadre = tk.Frame(racine, padx=12, pady=12)
        cadre.pack(fill="both", expand=True)

        tk.Label(cadre, text="Matricule").grid(row=0, column=0, sticky="w")
        self.champ_matricule = tk.Entry(cadre)
        self.champ_matricule.grid(row=0, column=1, sticky="ew", pady=2)

        tk.Label(cadre, text="Mot de passe maître").grid(row=1, column=0, sticky="w")
        self.champ_mdp = tk.Entry(cadre, show="*")
        self.champ_mdp.grid(row=1, column=1, sticky="ew", pady=2)

        tk.Button(cadre, text="Ouvrir une session",
                  command=self.ouvrir_session).grid(row=2, column=0, columnspan=2, pady=6)
        tk.Button(cadre, text="Afficher mes secrets",
                  command=self.afficher_secrets).grid(row=3, column=0, columnspan=2)

        self.liste = tk.Listbox(cadre, width=50, height=8)
        self.liste.grid(row=4, column=0, columnspan=2, pady=8, sticky="nsew")

        self.message = tk.Label(cadre, text="", fg="red", wraplength=380, justify="left")
        self.message.grid(row=5, column=0, columnspan=2, sticky="w")

        cadre.columnconfigure(1, weight=1)

    def ouvrir_session(self):
        try:
            self.session = self.coffre.ouvrir_session(
                self.champ_matricule.get(), self.champ_mdp.get())
            self.message.config(text="Session ouverte.", fg="green")
        except ErreurCoffre as erreur:
            self.message.config(text=f"Erreur : {erreur}", fg="red")

    def afficher_secrets(self):
        try:
            lignes = self.coffre.lister(self.session)
        except ErreurCoffre as erreur:
            self.message.config(text=f"Erreur : {erreur}", fg="red")
            return
        self.liste.delete(0, tk.END)
        for ligne in lignes:
            self.liste.insert(tk.END, ligne)
        self.message.config(text=f"{len(lignes)} secret(s).", fg="green")

    def quitter(self):
        self.coffre.fermer()
        self.racine.destroy()


def main():
    coffre = Coffre(CHEMIN_BD)
    racine = tk.Tk()
    Fenetre(racine, coffre)
    racine.mainloop()


if __name__ == "__main__":
    main()