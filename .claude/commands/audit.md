---
description: Audit hostile du projet par un agent neuf (sécurité, logique, stress test, design)
argument-hint: "[périmètre optionnel, ex. : paiements, V11, écran d'accueil]"
---

Lance l'agent `auditeur` (outil Agent, `subagent_type: "auditeur"`) pour auditer ce projet.

Périmètre : $ARGUMENTS (si vide : tout le projet).

Transmets-lui seulement : le chemin absolu de la racine du projet, le périmètre, la date et l'heure du jour.
- Aucun résumé de ce qui a été fait dans cette session, aucune explication de tes choix, aucun avis sur ce qui fonctionne.
- Rien sur ce qui a été corrigé récemment : il doit le découvrir seul.

Quand l'agent a rendu son rapport :
1. Enregistre le rapport complet, sans le couper ni l'adoucir, dans `audits/AAAA-MM-JJ-HHMM.md` à la racine du projet (crée le
   dossier si besoin). Ne le commite pas sans ma demande.
2. Affiche-moi le verdict, le top 5, le nombre de constats par gravité et le chemin du rapport.
3. Ne corrige RIEN. Demande-moi quels constats traiter et dans quel ordre.
