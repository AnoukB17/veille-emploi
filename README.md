# 🔎 Ma veille emploi

Chaque matin, un robot va chercher les offres d'emploi qui m'intéressent, garde celles qui correspondent à mes critères, puis les affiche sur ma page web.

## Comment c'est organisé

| Fichier | Rôle |
|---|---|
| `config.json` | **Mes réglages** : métiers recherchés, ville, mots à exclure… C'est le seul fichier à modifier au quotidien. |
| `collecte.py` | Le programme Python qui collecte, filtre et enregistre les offres. |
| `.github/workflows/collecte.yml` | Le « réveil » : demande à GitHub de lancer `collecte.py` chaque matin. |
| `docs/offres.json` | Les offres trouvées. C'est le robot qui remplit ce fichier. |
| `docs/entreprises.json` | Les entreprises à contacter en candidature spontanée (La Bonne Boite). |
| `docs/journal.txt` | Le compte rendu de la dernière collecte : pratique pour voir ce qui a marché ou non. |
| `docs/index.html` | Ma page web, qui affiche les offres et les entreprises. |

## Mise en route (à faire une seule fois)

### 1. Obtenir les clés France Travail (gratuit)
1. Va sur **francetravail.io**, crée un compte, puis une **application** dans ton espace.
2. Sur la page de l'application, clique sur **Ajouter une API** et ajoute **« La Bonne Boite »**
   (les entreprises à fort potentiel d'embauche).
3. Note l'**Identifiant client** et la **Clé secrète** de l'application.

> L'API **« Offres d'emploi v2 »** n'est plus proposée en libre accès aux nouvelles applications.
> Si tu l'obtiens un jour, ajoute-la à l'application puis passe `"france_travail"` à `true` dans `config.json`.

### 2. Ranger les clés dans le coffre-fort GitHub
Dans ce dépôt : **Settings → Secrets and variables → Actions → New repository secret**
- Nom : `FRANCE_TRAVAIL_CLIENT_ID`, valeur : l'Identifiant client
- Nom : `FRANCE_TRAVAIL_CLIENT_SECRET`, valeur : la Clé secrète

⚠️ Ne colle jamais ces clés directement dans un fichier du dépôt : il est public.

### 3. Activer la page web
**Settings → Pages** → Source : *Deploy from a branch* → Branch : `main`, dossier `/docs` → **Save**.
Ta page sera visible quelques minutes plus tard à l'adresse `https://<ton-pseudo>.github.io/veille-emploi/`.

### 4. Lancer une première collecte
Onglet **Actions → Collecte des offres → Run workflow**. Patiente environ 1 minute, puis ouvre ta page.

## Modifier ma recherche
Ouvre `config.json` sur GitHub, clique sur le crayon ✏️, modifie, puis **Commit changes**.

- `recherches` : les métiers ou mots-clés à chercher (une recherche par élément).
- `departement` : le numéro du département où chercher (`63` = Puy-de-Dôme).
- `mots_exclus` : une offre est écartée si son **titre** contient un de ces mots.
- `mots_obligatoires` : l'offre doit contenir **tous** ces mots, par exemple `["CDI"]`.
- `salaire_min` : salaire annuel minimum en euros (`0` = pas de filtre).
- `bonne_boite` → `metiers` : les métiers pour lesquels chercher des entreprises qui recrutent ; `distance_km` : le rayon autour de Clermont-Ferrand.
- `sources` → `adzuna` : source désactivée, car son API est devenue payante.
- `sources` → `remotive` : passe à `true` pour ajouter des offres en télétravail (souvent en anglais).

## Idées pour aller plus loin
- Ajouter les pages carrières de mes entreprises préférées.
- Recevoir un email quand il y a de nouvelles offres.
