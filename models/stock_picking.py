# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Champs BL de base uniquement
    delivery_note_number = fields.Char(
        string='N° BL',
        readonly=True,
        copy=False
    )

    is_delivery_note_printed = fields.Boolean(
        string='BL Imprimé',
        default=False
    )

    def action_generate_delivery_note(self):
        """Générer le numéro BL"""
        for picking in self:
            if not picking.delivery_note_number and picking.picking_type_code == 'outgoing':
                # Générer le numéro
                sequence = self.env['ir.sequence'].next_by_code('cpss.delivery.note')
                if sequence:
                    picking.delivery_note_number = sequence
                else:
                    # Fallback
                    year = fields.Date.today().year
                    picking.delivery_note_number = f"BL/{year}/{picking.id:05d}"

                # Marquer comme imprimé
                picking.is_delivery_note_printed = True

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Succès',
                'message': 'Bon de livraison généré !',
                'type': 'success',
            }
        }