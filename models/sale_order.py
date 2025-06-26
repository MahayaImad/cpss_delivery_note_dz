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

    # État de paiement calculé pour Odoo 16
    payment_state_computed = fields.Selection([
        ('not_paid', 'Non Payé'),
        ('in_payment', 'En Cours'),
        ('paid', 'Payé'),
        ('partial', 'Partiel'),
    ], string='État Paiement', compute='_compute_payment_state_computed', store=True)

    @api.depends('picking_ids.state')
    def _compute_delivery_note_count(self):
        """Calcule le nombre de livraisons validées (BL)"""
        for order in self:
            # Vérifier que picking_ids existe
            if hasattr(order, 'picking_ids'):
                # Compter les pickings sortants validés
                delivery_notes = order.picking_ids.filtered(
                    lambda p: p.picking_type_code == 'outgoing' and p.state == 'done'
                )
                order.delivery_note_count = len(delivery_notes)
            else:
                order.delivery_note_count = 0

    @api.depends('picking_ids.state')
    def _compute_delivery_note_status(self):
        """Calcule l'état global des BL"""
        for order in self:
            # Vérifier que picking_ids existe (relation avec stock)
            if not hasattr(order, 'picking_ids'):
                order.delivery_note_status = 'none'
                continue

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

    @api.depends('invoice_ids.amount_residual', 'invoice_ids.amount_total', 'invoice_ids.state')
    def _compute_payment_state_computed(self):
        """Calcule l'état de paiement depuis les factures pour Odoo 16"""
        for order in self:
            # Vérifier que invoice_ids existe
            if not hasattr(order, 'invoice_ids'):
                order.payment_state_computed = 'not_paid'
                continue

            invoices = order.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted'
            )

            if not invoices:
                order.payment_state_computed = 'not_paid'
                continue

            # Calculer les totaux avec vérifications
            total_amount = 0
            total_residual = 0

            for invoice in invoices:
                if hasattr(invoice, 'amount_total') and hasattr(invoice, 'amount_residual'):
                    total_amount += invoice.amount_total or 0
                    total_residual += invoice.amount_residual or 0

            # Déterminer l'état
            if total_amount == 0:
                order.payment_state_computed = 'not_paid'
            elif total_residual == 0:
                order.payment_state_computed = 'paid'
            elif total_residual == total_amount:
                order.payment_state_computed = 'not_paid'
            else:
                order.payment_state_computed = 'partial'

    def action_view_delivery_notes(self):
        """Ouvre la vue des bons de livraison de cette commande"""
        self.ensure_one()

        # Vérifier que picking_ids existe
        if not hasattr(self, 'picking_ids'):
            raise UserError(_("Ce module nécessite le module Stock pour fonctionner."))

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
                'default_sale_id': self.id,
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

    def action_create_delivery_note(self):
        """Créer une livraison depuis la commande (process standard)"""
        self.ensure_one()

        if self.state not in ['sale', 'done']:
            raise UserError(_("Impossible de créer une livraison pour une commande non confirmée."))

        # Vérifier que picking_ids existe
        if not hasattr(self, 'picking_ids'):
            raise UserError(_("Ce module nécessite le module Stock pour fonctionner."))

        # Vérifier s'il y a des pickings en attente
        pending_pickings = self.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing'
                      and p.state in ['confirmed', 'assigned', 'partially_available']
        )

        if not pending_pickings:
            # Pas de picking en attente, utiliser le process standard Odoo
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Information',
                    'message': 'Utilisez le bouton "Livraison" standard pour créer une livraison.',
                    'type': 'info',
                }
            }

        # Rediriger vers le premier picking disponible
        picking = pending_pickings[0]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': picking.id,
            'target': 'current',
        }


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
            # Vérifier que move_ids existe et est accessible
            if hasattr(line, 'move_ids') and line.move_ids:
                for move in line.move_ids:
                    if (hasattr(move, 'picking_id') and
                            move.picking_id and
                            move.picking_id.picking_type_code == 'outgoing' and
                            move.picking_id.state == 'done' and
                            move.state == 'done'):
                        qty += move.quantity_done or 0
            line.qty_delivered_bl = qty