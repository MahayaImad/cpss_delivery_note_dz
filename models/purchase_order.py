from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Compteur des bons de réception (basé sur les réceptions validées)
    receipt_note_count = fields.Integer(
        string='Nb. Bons de Réception',
        compute='_compute_receipt_note_count',
        help="Nombre de réceptions validées pour cette commande d'achat"
    )

    # État global des BR (Bons de Réception)
    receipt_note_status = fields.Selection([
        ('none', 'Aucun BR'),
        ('partial', 'BR Partiels'),
        ('done', 'BR Complets'),
    ], string='État BR', compute='_compute_receipt_note_status', store=True)

    # État de paiement calculé pour les achats
    payment_state_computed = fields.Selection([
        ('not_paid', 'Non Payé'),
        ('in_payment', 'En Cours'),
        ('paid', 'Payé'),
        ('partial', 'Partiel'),
    ], string='État Paiement', compute='_compute_payment_state_computed', store=True)

    @api.depends('picking_ids.state')
    def _compute_receipt_note_count(self):
        """Calcule le nombre de réceptions validées (BR)"""
        for order in self:
            # Compter les pickings entrants validés
            receipt_notes = order.picking_ids.filtered(
                lambda p: p.picking_type_code == 'incoming' and p.state == 'done'
            )
            order.receipt_note_count = len(receipt_notes)

    @api.depends('picking_ids.state')
    def _compute_receipt_note_status(self):
        """Calcule l'état global des BR"""
        for order in self:
            pickings = order.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming')

            if not pickings:
                order.receipt_note_status = 'none'
                continue

            # Compter les pickings validés
            done_pickings = pickings.filtered(lambda p: p.state == 'done')

            if not done_pickings:
                order.receipt_note_status = 'none'
            elif len(done_pickings) == len(pickings):
                order.receipt_note_status = 'done'
            else:
                order.receipt_note_status = 'partial'

    @api.depends('invoice_ids.amount_residual', 'invoice_ids.amount_total', 'invoice_ids.state')
    def _compute_payment_state_computed(self):
        """Calcule l'état de paiement depuis les factures d'achat"""
        for order in self:
            # Filtrer les factures fournisseur validées
            invoices = order.invoice_ids.filtered(
                lambda inv: inv.move_type == 'in_invoice' and inv.state == 'posted'
            )

            if not invoices:
                order.payment_state_computed = 'not_paid'
                continue

            # Calculer les totaux
            total_amount = sum(invoices.mapped('amount_total'))
            total_residual = sum(invoices.mapped('amount_residual'))

            # Déterminer l'état
            if total_amount == 0:
                order.payment_state_computed = 'not_paid'
            elif total_residual == 0:
                order.payment_state_computed = 'paid'
            elif total_residual == total_amount:
                order.payment_state_computed = 'not_paid'
            else:
                order.payment_state_computed = 'partial'

    def action_view_receipt_notes(self):
        """Ouvre la vue des bons de réception de cette commande d'achat"""
        self.ensure_one()

        # Récupérer les pickings validés (BR)
        receipt_pickings = self.picking_ids.filtered(
            lambda p: p.picking_type_code == 'incoming' and p.state == 'done'
        )

        action = {
            'name': _('Bons de Réception'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'target': 'current',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_origin': self.name,
            }
        }

        if len(receipt_pickings) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': receipt_pickings.id,
            })
        else:
            action['domain'] = [('id', 'in', receipt_pickings.ids)]

        return action

    def action_create_receipt_note(self):
        """Créer une réception depuis la commande d'achat (process standard)"""
        self.ensure_one()

        if self.state not in ['purchase', 'done']:
            raise UserError(_("Impossible de créer une réception pour une commande d'achat non confirmée."))

        # Vérifier s'il y a des pickings en attente
        pending_pickings = self.picking_ids.filtered(
            lambda p: p.picking_type_code == 'incoming'
                      and p.state in ['confirmed', 'assigned', 'partially_available']
        )

        if not pending_pickings:
            # Pas de picking en attente
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Information',
                    'message': 'Utilisez le bouton "Réception" standard pour créer une réception.',
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


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Quantité totale reçue avec BR
    qty_received_br = fields.Float(
        string='Qté Reçue (BR)',
        compute='_compute_qty_received_br',
        help="Quantité totale reçue dans les réceptions validées"
    )

    @api.depends('move_ids.quantity_done', 'move_ids.picking_id.state')
    def _compute_qty_received_br(self):
        """Calcule la quantité reçue dans les BR (réceptions validées)"""
        for line in self:
            qty = 0.0
            for move in line.move_ids:
                if (move.picking_id and
                    move.picking_id.picking_type_code == 'incoming' and
                    move.picking_id.state == 'done' and
                    move.state == 'done'):
                    qty += move.quantity_done or 0
            line.qty_received_br = qty