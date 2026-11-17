"""
collecte.py — le "robot" qui va chercher les offres d'emploi.

Ce qu'il fait, dans l'ordre :
  1. lit tes réglages dans config.json
  2. COLLECTE : interroge les sources (France Travail, Remotive...)
  3. FILTRE   : garde seulement les offres qui correspondent à tes critères
  4. STOCKE   : ajoute les nouvelles offres dans docs/offres.json
               (le fichier que lit ta page web)
  + BONUS     : liste les entreprises qui recrutent souvent (La Bonne Boite)
               dans docs/entreprises.json

GitHub Actions lance ce fichier automatiquement chaque matin.
Tu peux aussi le lancer toi-même sur ton ordinateur : python collecte.py
"""

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

FICHIER_CONFIG = "config.json"
FICHIER_OFFRES = "docs/offres.json"

# On note ici chaque problème rencontré pendant la collecte
ERREURS = []

# Tout ce que le robot affiche est aussi gardé ici, puis enregistré dans docs/journal.txt
# (pratique pour comprendre ce qui s'est passé sans fouiller dans GitHub Actions)
FICHIER_ENTREPRISES = "docs/entreprises.json"
FICHIER_JOURNAL = "docs/journal.txt"
JOURNAL = []
_afficher = print


def print(*morceaux):
    JOURNAL.append(" ".join(str(m) for m in morceaux))
    _afficher(*morceaux)


def detail_erreur(erreur):
    """Ajoute à une erreur web le message d'explication renvoyé par le site (s'il y en a un)."""
    texte = str(erreur)
    try:
        texte += " — " + erreur.read().decode("utf-8", "replace")[:300]
    except Exception:
        pass
    return texte


def jeton_france_travail(scopes_possibles):
    """Échange nos identifiants France Travail contre un "jeton" d'accès valable quelques minutes.
    On essaie chaque scope (= la liste des droits demandés) jusqu'à ce qu'un soit accepté."""
    client_id = (os.environ.get("FRANCE_TRAVAIL_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("FRANCE_TRAVAIL_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        print("⚠️  France Travail ignoré : clés FRANCE_TRAVAIL_CLIENT_ID / FRANCE_TRAVAIL_CLIENT_SECRET absentes (voir README).")
        return None

    derniere_erreur = None
    refus = []
    for scope in scopes_possibles:
        try:
            corps = urllib.parse.urlencode({
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": scope,
            }).encode("utf-8")
            requete = urllib.request.Request(
                "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire",
                data=corps,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(requete, timeout=30) as reponse:
                return json.loads(reponse.read().decode("utf-8"))["access_token"]
        except Exception as erreur:
            derniere_erreur = erreur
            refus.append(f"❌ France Travail, connexion refusée (droits « {scope} ») : {detail_erreur(erreur)}")
    for message in refus:
        print(message)
    # Diagnostic sans rien révéler : seulement la forme des deux valeurs
    print(f"   Diagnostic — identifiant : {len(client_id)} caractères, commence par « PAR_ » : "
          f"{'oui' if client_id.startswith('PAR_') else 'non'}, contient un espace ou un guillemet : "
          f"{'oui' if any(c in client_id for c in ' \t\n\"') else 'non'}")
    print(f"   Diagnostic — clé secrète : {len(client_secret)} caractères, commence par « PAR_ » : "
          f"{'oui' if client_secret.startswith('PAR_') else 'non'}, contient un espace ou un guillemet : "
          f"{'oui' if any(c in client_secret for c in ' \t\n\"') else 'non'}, "
          f"identique à l'identifiant : {'oui' if client_secret == client_id else 'non'}")
    print("   → Vérifie tes deux clés, et que l'API demandée est bien ajoutée à ton application sur francetravail.io.")
    ERREURS.append(derniere_erreur)
    return None


# ---------------------------------------------------------------------------
# Petit outil : télécharger une adresse web et lire la réponse en JSON
# ---------------------------------------------------------------------------
def telecharger_json(url):
    requete = urllib.request.Request(url, headers={"User-Agent": "veille-emploi/1.0"})
    with urllib.request.urlopen(requete, timeout=30) as reponse:
        return json.loads(reponse.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# 2. COLLECTE — une fonction par source
#    Chaque fonction renvoie une liste d'offres au MÊME format (un dictionnaire)
#    pour que la suite du programme n'ait pas à savoir d'où elles viennent.
# ---------------------------------------------------------------------------
def collecter_adzuna(config):
    """Adzuna : regroupe des offres de nombreux sites. Attention : API devenue payante (désactivée par défaut)."""
    # .strip() enlève les espaces ou retours à la ligne copiés par erreur
    app_id = (os.environ.get("ADZUNA_APP_ID") or "").strip()
    app_key = (os.environ.get("ADZUNA_APP_KEY") or "").strip()
    if not app_id or not app_key:
        print("⚠️  Adzuna ignoré : clés ADZUNA_APP_ID / ADZUNA_APP_KEY absentes (voir README).")
        return []

    offres = []
    for recherche in config["recherches"]:
        parametres = {
            "app_id": app_id,
            "app_key": app_key,
            "what": recherche,
            "where": config.get("lieu", ""),
            "distance": config.get("distance_km", 30),
            "results_per_page": 50,
            "max_days_old": 14,
            "sort_by": "date",
        }
        url = "https://api.adzuna.com/v1/api/jobs/fr/search/1?" + urllib.parse.urlencode(parametres)
        try:
            donnees = telecharger_json(url)
        except Exception as erreur:
            print(f"❌ Adzuna, recherche « {recherche} » : {erreur}")
            if "401" in str(erreur):
                print("   → Adzuna refuse tes clés : vérifie ADZUNA_APP_ID et ADZUNA_APP_KEY (voir README).")
            ERREURS.append(erreur)
            continue

        for o in donnees.get("results", []):
            offres.append({
                "titre": o.get("title", ""),
                "entreprise": o.get("company", {}).get("display_name", ""),
                "lieu": o.get("location", {}).get("display_name", ""),
                "description": o.get("description", ""),
                "salaire_min": o.get("salary_min"),
                "contrat": o.get("contract_type") or "",
                "lien": o.get("redirect_url", ""),
                "publiee_le": (o.get("created") or "")[:10],
                "source": "Adzuna",
                "recherche": recherche,
            })
        print(f"✅ Adzuna, « {recherche} » : {len(donnees.get('results', []))} offres")
    return offres


def collecter_france_travail(config):
    """France Travail (ex-Pôle emploi) : l'API officielle et gratuite, la plus grosse source en France."""
    # Étape A : obtenir un jeton d'accès
    jeton = jeton_france_travail(["api_offresdemploiv2 o2dsoffre"])
    if not jeton:
        return []

    # Étape B : une recherche par mot-clé, dans chaque groupe de départements
    # (France Travail accepte 5 départements au maximum par recherche)
    departements = config.get("departements") or [config.get("departement", "")]
    lots = [departements[i:i + 5] for i in range(0, len(departements), 5)]
    jours = config.get("jours_max", 31)   # valeurs acceptées par France Travail : 1, 3, 7, 14 ou 31

    offres = []
    for recherche in config["recherches"]:
        resultats = []
        echec = False
        for lot in lots:
            parametres = {
                "motsCles": recherche,
                "departement": ",".join(lot),
                "publieeDepuis": jours,
                "range": "0-149",         # les 150 premières offres (le maximum par appel)
            }
            url = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search?" + urllib.parse.urlencode(parametres)
            try:
                requete = urllib.request.Request(url, headers={"Authorization": "Bearer " + jeton, "Accept": "application/json"})
                with urllib.request.urlopen(requete, timeout=30) as reponse:
                    contenu = reponse.read().decode("utf-8")
                # Quand il n'y a aucune offre, France Travail renvoie une réponse vide
                resultats += json.loads(contenu).get("resultats", []) if contenu.strip() else []
            except Exception as erreur:
                print(f"❌ France Travail, recherche « {recherche} » ({','.join(lot)}) : {detail_erreur(erreur)}")
                ERREURS.append(erreur)
                echec = True
            time.sleep(0.4)   # petite pause : l'API limite le nombre d'appels par seconde
        if echec and not resultats:
            continue

        for o in resultats:
            lien = (o.get("origineOffre") or {}).get("urlOrigine") or \
                "https://candidat.francetravail.fr/offres/recherche/detail/" + str(o.get("id", ""))
            offres.append({
                "titre": o.get("intitule", ""),
                "entreprise": (o.get("entreprise") or {}).get("nom", "") or "Nom non communiqué",   # nom masqué par le recruteur
                "lieu": (o.get("lieuTravail") or {}).get("libelle", ""),
                "description": o.get("description", ""),
                "salaire_min": None,
                "contrat": o.get("typeContratLibelle") or o.get("typeContrat") or "",
                "lien": lien,
                "publiee_le": (o.get("dateCreation") or "")[:10],
                "source": "France Travail",
                "recherche": recherche,
            })
        print(f"✅ France Travail, « {recherche} » : {len(resultats)} offres")
    return offres


def collecter_remotive(config):
    """Remotive : offres en télétravail (souvent en anglais). Aucune clé nécessaire."""
    offres = []
    for recherche in config["recherches"]:
        url = "https://remotive.com/api/remote-jobs?" + urllib.parse.urlencode({"search": recherche})
        try:
            donnees = telecharger_json(url)
        except Exception as erreur:
            print(f"❌ Remotive, recherche « {recherche} » : {erreur}")
            ERREURS.append(erreur)
            continue

        for o in donnees.get("jobs", []):
            offres.append({
                "titre": o.get("title", ""),
                "entreprise": o.get("company_name", ""),
                "lieu": "Télétravail – " + (o.get("candidate_required_location") or ""),
                "description": o.get("description", ""),
                "salaire_min": None,
                "contrat": o.get("job_type") or "",
                "lien": o.get("url", ""),
                "publiee_le": (o.get("publication_date") or "")[:10],
                "source": "Remotive",
                "recherche": recherche,
            })
        print(f"✅ Remotive, « {recherche} » : {len(donnees.get('jobs', []))} offres")
    return offres


SOURCES = {
    "france_travail": collecter_france_travail,
    "adzuna": collecter_adzuna,
    "remotive": collecter_remotive,
}


# ---------------------------------------------------------------------------
# BONUS — La Bonne Boite : les entreprises qui ont de fortes chances d'embaucher
#         (pour envoyer des candidatures spontanées, même sans annonce publiée)
# ---------------------------------------------------------------------------
def collecter_bonne_boite(config):
    reglages = config.get("bonne_boite", {})
    jeton = jeton_france_travail(["api_labonneboitev2 search office", "api_labonneboitev2"])
    if not jeton:
        return []

    trouvees = {}   # siret -> entreprise (le siret est le numéro unique d'un établissement)
    # On peut chercher par nom de métier ("metiers") ou par code ROME ("codes_rome"),
    # le code officiel d'un métier chez France Travail (exemple : M1707)
    recherches = [("job", m) for m in reglages.get("metiers", [])] + \
                 [("rome", c) for c in reglages.get("codes_rome", [])]
    for critere, metier in recherches:
        parametres = {
            critere: metier,
            "latitude": reglages.get("latitude"),
            "longitude": reglages.get("longitude"),
            "distance": reglages.get("distance_km", 50),
            "page": 1,
            "page_size": 100,
        }
        url = "https://api.francetravail.io/partenaire/labonneboite/v2/recherche?" + urllib.parse.urlencode(parametres)
        try:
            requete = urllib.request.Request(url, headers={"Authorization": "Bearer " + jeton, "Accept": "application/json"})
            with urllib.request.urlopen(requete, timeout=30) as reponse:
                contenu = reponse.read().decode("utf-8")
            donnees = json.loads(contenu) if contenu.strip() else {}
        except Exception as erreur:
            print(f"❌ La Bonne Boite, métier « {metier} » : {detail_erreur(erreur)}")
            ERREURS.append(erreur)
            continue

        resultats = donnees.get("items") or donnees.get("companies") or [] if isinstance(donnees, dict) else donnees
        if resultats and not trouvees:
            # Pour vérifier le format des données la première fois
            print("   (champs reçus : " + ", ".join(sorted(resultats[0].keys())) + ")")
        for e in resultats:
            code_postal = str(e.get("postcode") or "")
            departement = config.get("departement", "")
            if departement and code_postal and not code_postal.startswith(departement):
                continue
            siret = str(e.get("siret") or "")
            if not siret or siret in trouvees:
                continue
            trouvees[siret] = {
                "nom": e.get("company_name") or e.get("office_name") or "",
                "ville": e.get("city") or "",
                "code_postal": code_postal,
                "secteur": e.get("naf_label") or "",
                "effectif_min": e.get("headcount_min"),
                "effectif_max": e.get("headcount_max"),
                "potentiel": e.get("hiring_potential"),
                "siret": siret,
                "lien": "https://annuaire-entreprises.data.gouv.fr/etablissement/" + siret,
                "metier": metier,
                "code_rome": e.get("rome") or "",
            }
        dans_dep = [e for e in resultats if str(e.get("postcode") or "").startswith(config.get("departement", ""))]
        codes = {}
        for e in dans_dep:
            codes[str(e.get("rome"))] = codes.get(str(e.get("rome")), 0) + 1
        print(f"✅ La Bonne Boite, « {metier} » : {len(resultats)} entreprises reçues, dont {len(dans_dep)} dans le département")
        if os.environ.get("EXPLORATION"):
            print(f"   total annoncé : {donnees.get('hits') if isinstance(donnees, dict) else '?'} · codes ROME : {codes}")
            print("   exemples : " + " ; ".join(f"{e.get('company_name')} ({e.get('naf_label')})" for e in dans_dep[:6]))
        time.sleep(0.6)   # l'API accepte 2 appels par seconde au maximum

    # Les recherches par code ROME sont les plus précises : on les place en premier,
    # puis on classe par potentiel d'embauche
    precis = set(reglages.get("codes_rome", []))
    entreprises = sorted(trouvees.values(), key=lambda e: (e["metier"] in precis, e["potentiel"] or 0), reverse=True)
    return entreprises[: reglages.get("nombre_max", 60)]


# ---------------------------------------------------------------------------
# 3. FILTRE — est-ce que cette offre m'intéresse ?
# ---------------------------------------------------------------------------
def sans_accents(texte):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", texte.lower()) if unicodedata.category(c) != "Mn")


def offre_interessante(offre, config):
    texte = (offre["titre"] + " " + offre["description"]).lower()

    # Un mot exclu dans le TITRE suffit à écarter l'offre
    # (on compare sans accents ni majuscules : "EMPLOYE" et "employé" sont pareils)
    titre = sans_accents(offre["titre"])
    for mot in config.get("mots_exclus", []):
        if sans_accents(mot) in titre:
            return False

    # Filtre strict : le TITRE doit contenir au moins un mot de mon domaine
    mots_titre = config.get("mots_titre", [])
    if mots_titre and not any(sans_accents(mot) in titre for mot in mots_titre):
        return False

    # Tous les mots obligatoires doivent apparaître (titre ou description)
    for mot in config.get("mots_obligatoires", []):
        if mot.lower() not in texte:
            return False

    # Salaire minimum (seulement si l'offre indique un salaire)
    salaire_min = config.get("salaire_min", 0)
    if salaire_min and offre["salaire_min"] and offre["salaire_min"] < salaire_min:
        return False

    return True


# ---------------------------------------------------------------------------
# 4. STOCKAGE — fusionner avec les offres déjà connues
# ---------------------------------------------------------------------------
def charger_offres_existantes():
    if not os.path.exists(FICHIER_OFFRES):
        return []
    with open(FICHIER_OFFRES, encoding="utf-8") as f:
        return json.load(f).get("offres", [])


def nettoyer_description(texte, longueur=400):
    """Enlève les balises HTML et raccourcit la description."""
    import re
    texte = re.sub(r"<[^>]+>", " ", texte or "")
    texte = re.sub(r"\s+", " ", texte).strip()
    return texte[:longueur] + ("…" if len(texte) > longueur else "")


def main():
    try:
        collecte_complete()
    finally:
        # Quoi qu'il arrive, on enregistre le journal de cette collecte
        os.makedirs(os.path.dirname(FICHIER_JOURNAL), exist_ok=True)
        with open(FICHIER_JOURNAL, "w", encoding="utf-8") as f:
            f.write("Collecte du " + datetime.now(timezone.utc).strftime("%d/%m/%Y à %H:%M UTC") + "\n\n")
            f.write("\n".join(JOURNAL) + "\n")


def collecte_complete():
    with open(FICHIER_CONFIG, encoding="utf-8") as f:
        config = json.load(f)

    aujourd_hui = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Bonus : entreprises à contacter en candidature spontanée
    entreprises = []
    if config.get("bonne_boite", {}).get("active"):
        entreprises = collecter_bonne_boite(config)
        if entreprises:
            with open(FICHIER_ENTREPRISES, "w", encoding="utf-8") as f:
                json.dump({"mise_a_jour": aujourd_hui, "entreprises": entreprises}, f, ensure_ascii=False, indent=1)
        print(f"🏢 {len(entreprises)} entreprise(s) à fort potentiel d'embauche dans {FICHIER_ENTREPRISES}")

    # Collecte de toutes les sources activées
    collectees = []
    for nom, active in config.get("sources", {}).items():
        if active and nom in SOURCES:
            collectees += SOURCES[nom](config)

    # Filtre
    retenues = [o for o in collectees if o["lien"] and offre_interessante(o, config)]
    print(f"🔎 {len(collectees)} offres collectées, {len(retenues)} correspondent à tes critères")

    # Fusion : le lien sert d'identifiant unique, pour ne jamais garder de doublon
    # On repasse aussi les offres déjà enregistrées au filtre, au cas où les réglages ont changé
    existantes = [o for o in charger_offres_existantes() if offre_interessante(o, config)]
    deja_vus = {o["lien"] for o in existantes}
    titres_vus = {(o["titre"].lower(), o["entreprise"].lower()) for o in existantes}

    nouvelles = 0
    for o in retenues:
        cle_titre = (o["titre"].lower(), o["entreprise"].lower())
        if o["lien"] in deja_vus or cle_titre in titres_vus:
            continue
        o["description"] = nettoyer_description(o["description"])
        o["ajoutee_le"] = aujourd_hui
        existantes.append(o)
        deja_vus.add(o["lien"])
        titres_vus.add(cle_titre)
        nouvelles += 1

    # On oublie les offres trop anciennes
    limite = (datetime.now(timezone.utc) - timedelta(days=config.get("garder_les_offres_pendant_jours", 45))).strftime("%Y-%m-%d")
    existantes = [o for o in existantes if o["ajoutee_le"] >= limite]

    # Les plus récentes en premier
    existantes.sort(key=lambda o: (o["ajoutee_le"], o["publiee_le"]), reverse=True)

    os.makedirs(os.path.dirname(FICHIER_OFFRES), exist_ok=True)
    with open(FICHIER_OFFRES, "w", encoding="utf-8") as f:
        json.dump({"mise_a_jour": aujourd_hui, "departements": config.get("departements", []), "offres": existantes},
                  f, ensure_ascii=False, indent=1)

    print(f"✨ {nouvelles} nouvelle(s) offre(s) — {len(existantes)} au total dans {FICHIER_OFFRES}")

    # Si AUCUNE source n'a répondu, on termine en erreur : GitHub affichera une croix rouge
    if ERREURS and not collectees and not entreprises:
        print("❌ Aucune source n'a fonctionné : regarde les messages ci-dessus.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
