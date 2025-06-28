{
    'name': 'CPSS - Bon de Livraison Algérie',
    'version': '16.0.1.0.0',
    'category': 'Sales',
    'summary': 'Gestion des bons de livraison conformes à la spécificité algérienne',
    'description': """
CPSS - Bon de Livraison Algérie
===============================

Module développé par CPSS pour la gestion des bons de livraison conformes à la réglementation algérienne.

✅ **Fonctionnalités Principales :**
• Livraisons clients et retours clients
• Réceptions fournisseurs et retours fournisseurs  
• Calculs automatiques des montants (retours en négatif)
• Rapports PDF conformes (avec/sans TVA)
• Vues complètes : Tree, Kanban, Pivot, Graph
• Filtres avancés et groupements intelligents
• Intégration sale.order et purchase.order

✅ **Vues Disponibles :**
• **14 vues BL Vente** : Tree avec totaux, Kanban, Pivot, Graph, etc.
• **14 vues BR Achat** : Tree avec totaux, Kanban, Pivot, Graph, etc.
• **Menus organisés** : Vente, Achat, Global consolidé
• **Actions rapides** : À facturer, Aujourd'hui, par type

✅ **Conformité Algérienne :**
• Format BL réglementaire DZ
• Montants en lettres (Dinars Algériens)  
• Zones de signature obligatoires
• Informations légales complètes

📊 **Dashboard disponible** : Module complémentaire "CPSS Dashboard BL"
🔧 **Support** : support@cpss.dz

Phase 2 (Prochainement) :
=========================
🔄 BL autonomes (sans commande préalable)
🔄 Paiement direct des BL (vente cash)
🔄 Facturation optionnelle depuis BL

    """,
    'contributors': [
            'Cedar Peak Systems & Solutions Team',
        ],
    'author': 'Cedar Peak Systems & Solutions (CPSS)',
    'website': 'https://cedarpss.com/',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
        'stock',
        'sale_stock',
        'purchase',
        'purchase_stock',
        'account',
    ],
    'data': [
        # Sécurité
        'security/ir.model.access.csv',

        # Données de base
        # 'data/sequence_data.xml',  # Désactivé

        # Vues principales
        'views/stock_picking_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',

        # Nouvelles vues étendues
        'views/delivery_note_vente_views.xml',  # Vues BL Vente complètes
        'views/receipt_note_achat_views.xml',  # Vues BR Achat complètes

        # Rapports
        'reports/delivery_note_report.xml',
        'reports/delivery_note_template.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 10,
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'post_init_hook': '_post_init_hook',  # Hook pour configuration initiale
}