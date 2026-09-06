---
name: infographie-massage-metamorphique
description: Utilise CE skill DÈS QUE l'utilisateur demande de créer, générer ou mettre à jour une infographie pour la page Instagram/Facebook de massage métamorphique de sa sœur, même sans demande explicite du nom du skill. Déclencheurs concrets : « fais-moi l'infographie pour le post de cette semaine », « j'ai le texte et la photo, tu peux assembler le visuel ? », « génère l'infographie sur [sujet] pour Diane », « voici le JSON et la photo, sors-moi le JPEG au format Instagram », « prépare le post du mercredi ». Produit un JPEG 1080x1350 (ratio 4:5) à partir d'un JSON structuré (titre, accroche, sections, CTA, hashtags) et d'une photo de contexte, dans la charte graphique fixe (beige/vert olive, titres serif, bande photo verticale à droite).
allowed-tools: Bash, Read, Write
---

# Infographie massage métamorphique

## Ce que fait ce skill (une seule tâche)

Assembler un JSON structuré + une photo JPEG/PNG en **une** infographie JPEG
1080x1350 px prête à poster sur Instagram/Facebook, dans la charte graphique
fixe de la page : fond crème en dégradé subtil, texte vert olive foncé
`#4B5A2E` pour les titres (Lora serif), texte courant brun très foncé en
sans-serif (Instrument Sans), accroche en police manuscrite (Caveat). La mise
en page (colonne de texte à gauche, bande photo verticale à droite avec fondu
sur le bord gauche, icônes en médaillons ligne-art, encart CTA encadré, pied
de page avec séparateur + hashtags + petit cœur) est calquée sur les gabarits
de référence validés par l'utilisatrice.

Si la demande de l'utilisateur dépasse ça (ex. « génère aussi le texte du
post », « publie-le directement sur Instagram », « crée-moi 5 variantes de
couleur », « ajoute des effets de papillons dorés / bougies flottantes sur la
photo ») — dis-le clairement et propose de traiter ça comme une tâche
séparée. Ce skill ne fait que l'assemblage visuel déterministe à partir d'un
texte déjà écrit et d'une photo déjà prête ; il ne génère ni ne retouche
la photo elle-même (les effets lumineux/particules dorés vus sur certains
posts sont ajoutés en amont à la photo, pas par ce script).

## Étape 0 — Vérifier les dépendances (à faire à chaque premier lancement de session)

Ce skill dépend de Python 3 et de la bibliothèque Pillow. Les polices
(Lora, Instrument Sans, Caveat) sont fournies avec le skill dans
`assets/fonts/` — aucun téléchargement n'est nécessaire pour elles. Avant
tout lancement du script, vérifie :

```bash
command -v python3 >/dev/null 2>&1 && python3 -c "import PIL" 2>/dev/null && echo OK
```

Si la sortie n'est pas `OK`, **arrête-toi immédiatement** et affiche à
l'utilisateur l'installation manquante avec la commande exacte pour son OS,
sans rien tenter d'autre :

- **macOS / Linux** : `pip3 install Pillow --break-system-packages` (ou `pip3 install Pillow` si la commande précédente échoue)
- **Windows** : `py -m pip install Pillow`

Ne contourne jamais cette étape et ne tente pas d'improviser un rendu sans Pillow.

## Étape 1 — Réunir les deux entrées

Le skill a besoin de :

1. Un **JSON structuré** avec au minimum `titre`, `sections` (liste de
   `{icone, titre_section, texte}`, 1 à 3 sections). `accroche`, `sous_titre`,
   `icone_entete`, `cta` (`{icone, texte, valeur}`) et `hashtags` sont
   optionnels mais fortement recommandés — c'est ce qui fait ressembler le
   rendu aux exemples validés. Dans `accroche`, `texte` (des sections comme
   du CTA), un mot ou groupe de mots peut être mis en gras avec `**...**`
   (ex. `"une **véritable reconnexion**"`) — c'est la seule mise en forme
   reconnue, elle est appliquée à la lettre, jamais interprétée ou ajoutée de
   ta propre initiative.
2. Une **photo de contexte** (JPEG ou PNG) qui habille la bande verticale à
   droite de l'infographie.

Si l'utilisateur ne fournit que l'un des deux, demande l'élément manquant —
ne fabrique jamais de texte ni ne choisis une photo à sa place.

### Icônes disponibles

`cerveau`, `papillon`, `feuille` (aussi utilisée pour la petite branche
décorative du coin supérieur gauche), `arbre`, `noeud`, `croix` (un « X »,
pour les listes « ce que ce n'est pas »), `colonne` (colonne vertébrale),
`silhouette` (silhouette + petit cœur, pour tout ce qui touche au corps/à
l'écoute de soi), `lotus`, `telephone`, `enveloppe`, `lien` (icône de
maillon, pour un renvoi vers un site), `question` (un simple « ? »), `coeur`.

Une icône inconnue ne fait pas planter le script (un simple cercle est
dessiné à la place), mais signale-le à l'utilisateur : ça vaut le coup de lui
proposer d'utiliser une icône existante ou d'en ajouter une nouvelle au
script (voir la fonction `ICONS` dans `scripts/generate_infographie.py`,
chaque icône est une petite fonction de dessin autonome).

Le skill accepte 1 à 3 sections. Au-delà, ou si les textes sont longs, le
script avertit d'un risque de débordement (voir Étape 2) plutôt que de
rétrécir les polices en douce.

## Étape 2 — Lancer le script (jamais de calcul à la main)

Tout le placement du texte, le retour à la ligne, le centrage vertical du
bloc de contenu, le redimensionnement de la photo et le dessin des icônes
sont **déterministes** et vivent dans `scripts/generate_infographie.py`. Tu
ne recalcules jamais toi-même une position, une taille de police ou une
coupure de ligne : tu lances le script, et s'il y a un problème de rendu, tu
corriges l'entrée (le JSON, le texte trop long) et tu relances.

```bash
python3 scripts/generate_infographie.py \
  --input <chemin_du_json> \
  --image <chemin_de_la_photo> \
  --output <chemin_de_sortie.jpeg>
```

Le script renvoie un JSON sur stdout avec `fichier_genere`, `dimensions`,
`nb_sections` et `avertissements`. Lis toujours ce champ `avertissements` :

- Un avertissement de **débordement** (texte des sections ou du CTA qui
  empiète sur le pied de page, ou hashtags coupés au-delà de 2 lignes) veut
  dire qu'un texte est trop long pour le format — raccourcis-le dans le JSON
  et relance. Ne redimensionne jamais les polices toi-même pour compenser.
- Un avertissement d'**icône inconnue** est informatif : le rendu reste
  valide (un cercle simple remplace l'icône), mais préviens l'utilisateur.

Si le script sort en erreur (code de sortie différent de 0), le message
d'erreur JSON sur stderr indique exactement quel champ corriger (`titre`
manquant, `cta.texte` manquant si `cta` est fourni, section sans `texte`,
photo introuvable...). Corrige l'entrée, ne modifie jamais le script pour
« passer outre » une validation.

### Exemple de JSON valide

```json
{
  "titre": "La clarté",
  "sous_titre": "La Tête",
  "icone_entete": "cerveau",
  "accroche": "Mettre le mental sur pause\npour laisser le papillon s'envoler…",
  "sections": [
    {
      "icone": "cerveau",
      "titre_section": "",
      "texte": "Pour clore une séance de Massage Métamorphique, le soin se concentre sur la **tête**. Cette zone est en lien direct avec notre sphère de **pensée et de réflexion**."
    },
    {
      "icone": "papillon",
      "titre_section": "",
      "texte": "C'est ici que se joue notre capacité à accueillir le **changement** et à intégrer les transformations de la vie avec plus de **sérénité**."
    }
  ],
  "cta": {
    "icone": "telephone",
    "texte": "Tenté(e) par le Massage Métamorphique ? Prenez rendez-vous au",
    "valeur": "0475 69 00 84"
  },
  "hashtags": "#clartémentale #massage #bienetre #metamorphose #serenite"
}
```

`sous_titre` est affiché entre parenthèses juste après `titre`, sur la même
ligne (ex. « La clarté (La Tête) »). `titre_section` peut être laissé vide
(`""`) quand le texte de la section n'a pas besoin de son propre sous-titre
en gras — c'est le cas dans l'exemple ci-dessus.

## Étape 3 — Préférences réutilisables (fiche mémoire)

Le style graphique est fixe (défini dans le script) : tu ne poses **jamais**
de question dessus. `memoire.json`, à la racine du skill, sert uniquement à
retenir les valeurs qui reviennent d'une infographie à l'autre :
`cta_texte_defaut`, `cta_url_defaut`, `cta_icone_defaut`, `hashtags_frequents`.

Règles :

- **Produis toujours un premier résultat avant de poser une question.** Si
  le JSON fourni n'a pas de `cta`/`hashtags` complet mais que `memoire.json`
  en contient un, utilise-le automatiquement (sans demander) pour compléter
  les champs manquants. Si la mémoire est vide aussi, demande le texte et la
  valeur (numéro ou URL) du CTA — ce sont des champs obligatoires dès que
  `cta` est fourni, contrairement à `hashtags` qui est optionnel. Une fois le
  résultat montré, pose **une seule question** : « Veux-tu que je retienne ce
  texte/cette valeur de CTA par défaut pour les prochaines infographies ? »
  Jamais plusieurs questions à la fois, jamais de formulaire.
- Si l'utilisateur colle un exemple de JSON déjà complet, apprends-en
  directement les valeurs par défaut sans les lui redemander sous forme de
  question abstraite — propose simplement : « Je retiens ce CTA pour la
  prochaine fois ? »
- Si l'utilisateur dit « oublie mes infos » (ou équivalent) à propos de ce
  skill, remets les valeurs de `memoire.json` à `null` — ne le laisse jamais
  traîner avec des données que l'utilisateur a demandé à effacer.

## Étape 4 — Livrer

Montre le fichier JPEG généré à l'utilisateur. Mentionne le chemin de sortie
et, s'il y a eu des avertissements non bloquants (icône inconnue, champ
optionnel absent), résume-les en une phrase.

---

**Prochaine étape** : une fois l'infographie validée par l'utilisateur,
demande-lui si elle correspond bien au rendu attendu pour ce type de post
(découverte, témoignage, conseil pratique...) ou si un ajustement de contenu
(pas de style) est nécessaire avant de relancer le script.
