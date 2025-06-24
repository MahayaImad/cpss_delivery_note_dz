{
    'name': 'CPSS - Bon de Livraison Algérie',
    'version': '16.0.1.0.0',
    'category': 'Sales',
    'summary': 'Gestion des bons de livraison conformes à la spécificité algérienne',
    'description': """
CPSS - Bon de Livraison Algérie
===============================

Module développé par CPSS pour la gestion des bons de livraison conformes à la spécificité algérienne.

Fonctionnalités :
* Numérotation spécifique des BL (BL/YYYY/XXXXX)
* Calcul des montants basés sur les quantités livrées
* Suivi des états d'impression et de livraison
* Intégration avec les commandes de vente
* Rapports personnalisés pour l'Algérie

Phase 1 : BL depuis commandes de vente
Phase 2 : BL autonomes avec paiement direct (à venir)

Développé spécialement pour le marché algérien.
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
        'account',
    ],
    'data': [
        #'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/stock_picking_views.xml',
        #'views/sale_order_views.xml',
        #'reports/delivery_note_report.xml',
        #'reports/delivery_note_template.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}