# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Compteur des bons de livraison (basé sur les livraisons validées)
    delivery_note_count = fields.Integer(
        string='Nb. Bons de Livraison',
        compute='_compute_delivery_note_count',
        help="Nombre de livraisons validées pour cette commande"
    )

    # État global des BL
    delivery_note_status = fields.Selection([
        ('none', 'Aucun BL'),
        ('partial', 'BL Partiels'),
        ('done', 'BL Complets'),
    ], string='État BL', compute='_compute_delivery_note_status', store=True)

    @api.depends('picking_ids.state')
    def _compute_delivery_note_count(self):
        """Calcule le nombre de livraisons validées (BL)"""
        for order in self:
            # Les picking_ids existent toujours dans sale.order (module sale_stock)
            delivery_notes = order.picking_ids.filtered(
                lambda p: p.picking_type_code == 'outgoing' and p.state == 'done'
            )
            order.delivery_note_count = len(delivery_notes)

    @api.depends('picking_ids.state')
    def _compute_delivery_note_status(self):
        """Calcule l'état global des BL"""
        for order in self:
            pickings = order.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')

            if not pickings:
                order.delivery_note_status = 'none'
                continue

            # Compter les pickings validés
            done_pickings = pickings.filtered(lambda p: p.state == 'done')

            if not done_pickings:
                order.delivery_note_status = 'none'
            elif len(done_pickings) == len(pickings):
                order.delivery_note_status = 'done'
            else:
                order.delivery_note_status = 'partial'

    def action_view_delivery_notes(self):
        """Ouvre la vue des bons de livraison de cette commande"""
        self.ensure_one()

        # Récupérer les pickings validés (BL)
        delivery_pickings = self.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing' and p.state == 'done'
        )

        action = {
            'name': _('Bons de Livraison'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'target': 'current',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_origin': self.name,
            }
        }

        if len(delivery_pickings) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': delivery_pickings.id,
            })
        else:
            action['domain'] = [('id', 'in', delivery_pickings.ids)]

        return action


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Quantité totale livrée avec BL
    qty_delivered_bl = fields.Float(
        string='Qté Livrée (BL)',
        compute='_compute_qty_delivered_bl',
        help="Quantité totale livrée dans les livraisons validées"
    )

    @api.depends('move_ids.quantity_done', 'move_ids.picking_id.state')
    def _compute_qty_delivered_bl(self):
        """Calcule la quantité livrée dans les BL (livraisons validées)"""
        for line in self:
            qty = 0.0
            for move in line.move_ids:
                if (move.picking_id and
                    move.picking_id.picking_type_code == 'outgoing' and
                    move.picking_id.state == 'done' and
                    move.state == 'done'):
                    qty += move.quantity_done or 0
            line.qty_delivered_bl = qty