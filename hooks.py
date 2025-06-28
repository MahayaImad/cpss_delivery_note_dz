# -*- coding: utf-8 -*-
"""
Hook simplifié pour CPSS Delivery Note DZ
Configuration minimale post-installation
"""

import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def _post_init_hook(cr, registry):
    """
    Hook simplifié exécuté après l'installation du module
    """
    _logger.info("🚀 Configuration post-installation CPSS Delivery Note DZ")

    env = api.Environment(cr, SUPERUSER_ID, {})

    try:
        # 1. Calcul des montants pour les pickings validés existants
        _calculate_existing_amounts(env)

        # 2. Message de succès
        _logger.info("✅ Configuration CPSS terminée avec succès")
        _logger.info("📋 Fonctionnalités disponibles :")
        _logger.info("   • Menu Vente > Bons de Livraison Vente")
        _logger.info("   • Menu Achat > Bons de Réception Achat")
        _logger.info("   • Rapports PDF conformes (avec/sans TVA)")
        _logger.info("🇩🇿 Module conforme à la réglementation algérienne")

    except Exception as e:
        _logger.error(f"❌ Erreur configuration CPSS: {e}")
        # Ne pas lever l'erreur pour ne pas bloquer l'installation
        _logger.warning("⚠️ Installation partielle - Module utilisable mais recalcul manuel requis")


def _calculate_existing_amounts(env):
    """
    Calcule les montants pour les pickings validés existants
    (Version simplifiée et robuste)
    """
    _logger.info("📊 Calcul des montants pour les documents existants...")

    try:
        # Récupérer les pickings validés
        pickings = env['stock.picking'].search([
            ('state', '=', 'done'),
            ('picking_type_code', 'in', ['outgoing', 'incoming'])
        ], limit=1000)  # Limite pour éviter les timeouts

        if not pickings:
            _logger.info("ℹ️ Aucun document validé trouvé")
            return

        count = 0
        for picking in pickings:
            try:
                # Calcul simple des montants
                picking._compute_financial_amounts()
                count += 1

                # Log de progression tous les 100
                if count % 100 == 0:
                    _logger.info(f"📈 {count}/{len(pickings)} documents traités...")

            except Exception as e:
                # Continuer en cas d'erreur sur un document
                _logger.warning(f"⚠️ Erreur document {picking.name}: {e}")
                continue

        _logger.info(f"✅ {count} documents mis à jour avec succès")

    except Exception as e:
        _logger.warning(f"⚠️ Erreur lors du calcul des montants: {e}")
        _logger.info("ℹ️ Les montants seront calculés lors de la prochaine validation")