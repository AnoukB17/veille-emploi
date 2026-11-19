# Ma veille emploi

Plateforme personnelle de veille des offres d'emploi en **e-commerce et marketing digital**, centrée sur le **Puy-de-Dôme** et les départements voisins.

Chaque matin, un programme Python interroge l'API officielle de **France Travail**, garde les offres qui correspondent aux critères choisis, puis les publie sur une page web. Sur cette page, on peut rechercher et filtrer les offres, en mettre en favori et suivre ses candidatures.

- **Page web :** https://anoukb17.github.io/veille-emploi/
- **Code source :** https://github.com/AnoukB17/veille-emploi

Projet académique, personnel et non commercial.

---

## 1. Fonctionnement général

```
  Tous les matins (GitHub Actions)
            │
            ▼
  ┌───────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
  │ 1. COLLECTE           │ →  │ 2. FILTRE            │ →  │ 3. STOCKAGE          │
  │ API France Travail    │    │ mots du titre,       │    │ docs/offres.json     │
  │ (Offres d'emploi v2)  │    │ mots exclus,         │    │ sans doublons,       │
  │ 10 mots-clés          │    │ doublons             │    │ 45 jours maximum     │
  │ × 6 départements      │    │                      │    │                      │
  └───────────────────────┘    └──────────────────────┘    └──────────┬───────────┘
                                                                      │
                                                                      ▼
                                                     ┌────────────────────────────────┐
                                                     │ 4. AFFICHAGE (GitHub Pages)    │
                                                     │ docs/index.html lit le fichier │
                                                     │ et affiche les offres          │
                                                     └────────────────────────────────┘
```

1. **Collecte** : le programme demande un jeton d'accès à France Travail (OAuth2), puis lance une recherche par mot-clé sur les offres publiées au cours des 31 derniers jours.
2. **Filtre** : une offre n'est gardée que si son **titre** contient au moins un mot du domaine (e-commerce, digital, web, marketing…) et ne contient aucun mot exclu (stage, vendeur, employé…). Les doublons sont retirés.
3. **Stockage** : les offres retenues sont ajoutées au fichier `docs/offres.json`. Les offres de plus de 45 jours sont supprimées automatiquement.
4. **Affichage** : la page `docs/index.html`, publiée avec GitHub Pages, lit ce fichier et affiche les offres.

## 2. Organisation des fichiers

| Fichier | Rôle |
|---|---|
| `config.json` | Les réglages de la recherche : mots-clés, départements, période, filtres. |
| `collecte.py` | Le programme Python : collecte, filtre et enregistrement des offres. |
| `.github/workflows/collecte.yml` | L'automatisation : GitHub lance `collecte.py` chaque matin, puis enregistre le résultat. |
| `docs/index.html` | La page web (HTML, CSS et JavaScript, sans bibliothèque externe). |
| `docs/offres.json` | Les offres retenues, rempli par le programme. |
| `docs/journal.txt` | Le compte rendu de la dernière collecte (sources interrogées, nombre d'offres, erreurs). |
| `docs/entreprises.json` | Fonction optionnelle « entreprises à contacter » (API La Bonne Boite), désactivée par défaut. |

## 3. Choix techniques

- **Python sans dépendance externe** : seule la bibliothèque standard est utilisée (`urllib`, `json`), donc il n'y a rien à installer.
- **API officielle plutôt que scraping** : les données viennent de l'API de France Travail, qui autorise leur réutilisation. On ne lit pas les pages des sites d'emploi, qui l'interdisent souvent dans leurs conditions d'utilisation.
- **Hébergement gratuit avec GitHub** : GitHub Actions lance la collecte, GitHub Pages publie la page. Aucun serveur n'est nécessaire.
- **Clés d'API protégées** : l'identifiant et la clé secrète sont rangés dans les *Secrets* de GitHub. Ils n'apparaissent jamais dans le code.
- **Respect de l'API** : une seule collecte par jour, des pauses entre les requêtes, et une nouvelle tentative automatique si l'API répond « trop de demandes » (erreur 429).
- **Données personnelles** : la page ne collecte rien sur ses visiteurs. Les favoris et le suivi des candidatures sont enregistrés uniquement dans le navigateur (`localStorage`).

## 4. Fonctionnalités de la page

- Une recherche par mot-clé (intitulé, entreprise, ville, description).
- Des filtres : suivi (nouvelles, non consultées, favoris, candidatures envoyées), département et type de contrat, avec le nombre d'offres pour chacun.
- Des indicateurs : offres suivies, nouvelles offres, favoris, candidatures.
- Pour chaque offre : un lien vers l'annonce d'origine sur France Travail, un bouton favori, et des boutons « candidature envoyée » et « consultée ».
- Une mise en page adaptée au téléphone et un mode sombre automatique.

## 5. Réglages (`config.json`)

| Réglage | Rôle | Valeur actuelle |
|---|---|---|
| `recherches` | Mots-clés envoyés à l'API | e-commerce, chef de projet digital, marketing digital, community manager… |
| `departements` | Départements interrogés | 63, 03, 15, 43, 42, 69 |
| `jours_max` | Ancienneté maximale des offres (1, 3, 7, 14 ou 31 jours) | 31 |
| `mots_titre` | Le titre doit contenir au moins un de ces mots | e-commerce, digital, web, marketing… |
| `mots_exclus` | Une offre est écartée si son titre contient un de ces mots | stage, alternance, vendeur, employé… |
| `garder_les_offres_pendant_jours` | Durée de conservation d'une offre | 45 |

## 6. Installer le projet sur un autre compte

1. Créer un compte sur **francetravail.io**, puis une application, et demander l'accès à l'API **« Offres d'emploi v2 »**. Cet accès est soumis à conditions et se demande par le formulaire de contact du site.
2. Copier ce dépôt sur GitHub.
3. Dans **Settings → Secrets and variables → Actions**, ajouter deux secrets : `FRANCE_TRAVAIL_CLIENT_ID` et `FRANCE_TRAVAIL_CLIENT_SECRET`.
4. Dans **Settings → Pages**, publier la branche `main`, dossier `/docs`.
5. Lancer une première collecte : **Actions → Collecte des offres → Run workflow**.

Pour lancer la collecte sur son ordinateur (Python 3.9 ou plus) :

```bash
export FRANCE_TRAVAIL_CLIENT_ID="..."
export FRANCE_TRAVAIL_CLIENT_SECRET="..."
python collecte.py
```

Pour voir la page en local, servir le dossier `docs` (par exemple avec `python -m http.server` lancé dans ce dossier), puis ouvrir http://localhost:8000.

## 7. Limites connues

- **Une seule source** : seules les offres publiées sur France Travail sont collectées. Celles qui ne paraissent que sur LinkedIn, Indeed ou le site d'une entreprise n'apparaissent pas.
- **Filtre sur le titre** : une offre pertinente dont le titre ne contient aucun mot du domaine peut être écartée.
- **Nom du recruteur** : certains recruteurs choisissent de masquer leur nom sur France Travail. La page affiche alors « Recruteur non communiqué ».
- **Horaire de collecte** : GitHub peut retarder les tâches programmées de plusieurs heures quand ses serveurs sont chargés.
- **Favoris locaux** : les favoris et le suivi des candidatures ne se synchronisent pas d'un appareil à l'autre.

## 8. Historique du projet

Plusieurs sources ont été envisagées avant d'arriver à la version actuelle :

- **Adzuna** : abandonnée, car son API est devenue payante.
- **France Travail, Offres d'emploi v2** : retirée du libre accès pour les nouvelles applications. L'accès a été obtenu sur demande.
- **France Travail, La Bonne Boite** : testée pour lister des entreprises à contacter en candidature spontanée. Les résultats étaient peu pertinents pour ce métier, et la fonction a été désactivée.
- **Scraping des sites d'emploi** : écarté, car beaucoup de sites l'interdisent dans leurs conditions d'utilisation.

Le code a été écrit avec l'aide d'un assistant IA (Claude). Le traitement des offres, lui, n'utilise aucune IA : le tri se fait par mots-clés.
