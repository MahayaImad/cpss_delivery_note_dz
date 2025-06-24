# CPSS - Bon de Livraison Algérie

Module Odoo 16 pour la gestion des bons de livraison conformes au context  algérien.

## 📋 Fonctionnalités

### Phase 1 (Actuelle)
- ✅ **Numérotation automatique** des BL (format: BL/YYYY/XXXXX)
- ✅ **Calcul des montants** basés sur les quantités réellement livrées
- ✅ **Suivi des états** d'impression et de livraison
- ✅ **Intégration complète** avec les commandes de vente
- ✅ **Rapport PDF personnalisé** conforme au context  algérien
- ✅ **Filtres avancés** (BL non facturés, non payés, etc.)
- ✅ **Menu dédié** pour la gestion des bons de livraison

### Phase 2 (Prochainement)
- 🔄 BL autonomes (sans commande préalable)
- 🔄 Paiement direct des BL (vente cash)
- 🔄 Rapports client complets
- 🔄 Facturation optionnelle depuis BL

## 🚀 Installation

1. Copier le module dans le dossier `addons` d'Odoo
2. Redémarrer Odoo avec `--update-addons-path`
3. Aller dans **Apps** → Rechercher "CPSS"
4. Cliquer sur **Installer**

## 📁 Structure du Module

```
cpss_delivery_note_dz/
├── __manifest__.py              # Configuration du module
├── models/                      # Modèles de données
│   ├── stock_picking.py         # Extension des livraisons
│   └── sale_order.py           # Extension des commandes
├── views/                       # Interfaces utilisateur
│   ├── stock_picking_views.xml  # Vues des livraisons
│   └── sale_order_views.xml    # Vues des commandes
├── reports/                     # Rapports PDF
│   ├── delivery_note_report.xml
│   └── delivery_note_template.xml
├── data/                        # Données de base
│   └── sequence_data.xml        # Séquence numérotation
└── security/                    # Permissions
    └── ir.model.access.csv
```

## 🎯 Utilisation

### Générer un Bon de Livraison

1. **Depuis une commande de vente :**
   - Ouvrir la commande confirmée
   - Cliquer sur **"Créer BL"** ou **"Bons de Livraison"**
   - Dans la livraison, cliquer **"Générer BL"**

2. **Depuis le menu Livraisons :**
   - Aller dans **Ventes** → **Bons de Livraison**
   - Ouvrir une livraison
   - Cliquer **"Générer BL"**

### Imprimer un Bon de Livraison

- Bouton **"Imprimer BL"** dans la livraison
- Ou via **Imprimer** → **Bon de Livraison**

### Filtres Disponibles

- 📋 **Avec Bon de Livraison** : Toutes les livraisons avec BL
- ✅ **BL Imprimés** : BL déjà générés
- ⏳ **BL Non Imprimés** : BL en attente d'impression
- 💰 **BL Non Facturés** : Livraisons non encore facturées
- 💳 **BL Non Payés** : Livraisons non encore payées

## 🔧 Configuration

### Numérotation des BL
La séquence est automatiquement créée avec le format `BL/YYYY/XXXXX`.
Pour modifier : **Paramètres** → **Séquences & Identifiants** → "Bon de Livraison"

### Permissions
- **Utilisateur Stock** : Peut créer et imprimer les BL
- **Responsable Stock** : Accès complet + suppression

## 📊 Rapport PDF

Le bon de livraison inclut :

- 📋 **Informations complètes** expéditeur/destinataire
- 📦 **Détail des produits** avec quantités commandées/livrées
- 💰 **Calculs précis** des montants HT/TVA/TTC
- ✍️ **Zones de signature** (Livreur, Responsable, Client)
- 🏢 **Conformité réglementaire** algérienne

## 🆘 Support

Pour toute question ou assistance :
- **Email** : support@cpss.dz
- **Documentation** : [Wiki interne CPSS]

## 📝 Changelog

### Version 16.0.1.0.0 (2025-06-23)
- ✨ Version initiale
- 🎯 Phase 1 complète
- 📄 Rapport PDF optimisé
- 🔒 Sécurité configurée

---

**Développé par CPSS** 🇩🇿  
*Spécialement pour le marché algérien*