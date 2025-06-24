# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Compteur des bons de livraison
    delivery_note_count = fields.Integer(
        string='Nb. Bons de Livraison',
        compute='_compute_delivery_note_count',
        help="Nombre de bons de livraison générés pour cette commande"
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

    @api.depends('picking_ids.delivery_note_number')
    def _compute_delivery_note_count(self):
        """Calcule le nombre de BL générés"""
        for order in self:
            # Compter les pickings sortants avec un numéro BL
            delivery_notes = order.picking_ids.filtered(
                lambda p: p.picking_type_code == 'outgoing' and p.delivery_note_number
            )
            order.delivery_note_count = len(delivery_notes)

    @api.depends('picking_ids.delivery_note_number', 'picking_ids.state')
    def _compute_delivery_note_status(self):
        """Calcule l'état global des BL"""
        for order in self:
            pickings = order.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')

            if not pickings:
                order.delivery_note_status = 'none'
                continue

            bl_pickings = pickings.filtered(lambda p: p.delivery_note_number)

            if not bl_pickings:
                order.delivery_note_status = 'none'
            elif len(bl_pickings) == len(pickings.filtered(lambda p: p.state == 'done')):
                order.delivery_note_status = 'done'
            else:
                order.delivery_note_status = 'partial'

    @api.depends('invoice_ids.amount_residual', 'invoice_ids.amount_total', 'invoice_ids.state')
    def _compute_payment_state_computed(self):
        """Calcule l'état de paiement depuis les factures pour Odoo 16"""
        for order in self:
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

        # Récupérer les pickings avec BL
        delivery_pickings = self.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing' and p.delivery_note_number
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
                'search_default_delivery_notes': 1,
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
        """Créer un nouveau bon de livraison depuis la commande"""
        self.ensure_one()

        if self.state not in ['sale', 'done']:
            raise UserError(_("Impossible de créer un BL pour une commande non confirmée."))

        # Vérifier s'il y a des pickings en attente
        pending_pickings = self.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing'
                      and p.state in ['confirmed', 'assigned', 'partially_available']
        )

        if not pending_pickings:
            raise UserError(_("Aucune livraison en attente pour cette commande."))

        # Prendre le premier picking disponible
        picking = pending_pickings[0]

        # Rediriger vers la génération du BL
        return picking.action_generate_delivery_note()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Quantité total livrée avec BL
    qty_delivered_bl = fields.Float(
        string='Qté Livrée (BL)',
        compute='_compute_qty_delivered_bl',
        help="Quantité totale livrée avec bon de livraison"
    )

    @api.depends('move_ids.quantity_done', 'move_ids.picking_id.delivery_note_number')
    def _compute_qty_delivered_bl(self):
        """Calcule la quantité livrée avec BL uniquement"""
        for line in self:
            qty = 0.0
            # Vérifier que move_ids existe et est accessible
            if hasattr(line, 'move_ids'):
                for move in line.move_ids:
                    if (hasattr(move, 'picking_id') and
                            move.picking_id and
                            hasattr(move.picking_id, 'delivery_note_number') and
                            move.picking_id.delivery_note_number and
                            move.picking_id.picking_type_code == 'outgoing' and
                            move.state == 'done'):
                        qty += move.quantity_done or 0
            line.qty_delivered_bl = qty