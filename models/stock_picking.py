# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Champs BL de base uniquement
    delivery_note_number = fields.Char(
        string='N° BL',
        readonly=True,
        copy=False
    )

    delivery_note_date = fields.Datetime(
        string='Date BL',
        readonly=True,
        copy=False,
        help="Date de génération du bon de livraison"
    )

    is_delivery_note_printed = fields.Boolean(
        string='BL Imprimé',
        default=False
    )

    # Champs calculés pour les totaux (utilisés dans le rapport)
    amount_untaxed = fields.Monetary(
        string='Montant HT',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id'
    )

    amount_tax = fields.Monetary(
        string='TVA',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id'
    )

    amount_total = fields.Monetary(
        string='Total TTC',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id'
    )

    # NOUVEAU : Champ pour le montant en lettres
    amount_total_text = fields.Text(
        string='Montant en lettres',
        compute='_compute_amount_total_text',
        store=True,
        help="Montant total TTC en lettres"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        compute='_compute_currency_id',
        store=True
    )

    # États pour le rapport
    sale_invoice_status = fields.Selection(
        related='sale_id.invoice_status',
        string='État Facturation'
    )

    sale_payment_state = fields.Selection(
        related='sale_id.payment_state_computed',
        string='État Paiement'
    )

    @api.depends('company_id', 'sale_id.currency_id')
    def _compute_currency_id(self):
        """Calcule la devise depuis la commande ou la société"""
        for picking in self:
            if picking.sale_id and picking.sale_id.currency_id:
                picking.currency_id = picking.sale_id.currency_id
            else:
                picking.currency_id = picking.company_id.currency_id

    @api.depends('amount_total', 'currency_id')
    def _compute_amount_total_text(self):
        """Calcule le montant en lettres"""
        for record in self:
            record.amount_total_text = record.custom_amount_to_text(record.amount_total)

    def custom_amount_to_text(self, montant):
        """Convertit un montant en texte avec formatage spécifique pour l'Algérie"""
        currency_id = self.currency_id or self.env.ref('base.DZD')

        if not montant:
            return "Zéro dinar algérien"

        res = currency_id.amount_to_text(montant)

        # Ajustements spécifiques pour l'Algérie
        if round(montant % 1, 2) == 0.0:
            res += " et zéro centime"

        if montant > 1.0:
            res = res.replace('Dinar', 'Dinars')

        # Formatage pour l'Algérie
        res = res.replace('Dinar Algérien', 'Dinar Algérien')
        res = res.replace('Centimes', 'Centimes')

        return res.lower().capitalize()

    @api.depends('move_ids_without_package.price_unit', 'move_ids_without_package.quantity_done',
                 'move_ids_without_package.product_id.taxes_id')
    def _compute_amounts(self):
        """Calcule les montants basés sur les quantités livrées"""
        for picking in self:
            amount_untaxed = 0.0
            amount_tax = 0.0

            for move in picking.move_ids_without_package:
                if move.state == 'cancel':
                    continue

                # Utiliser la quantité livrée
                qty = move.quantity_done if move.quantity_done else move.product_uom_qty

                # Prix unitaire depuis la ligne de commande
                price_unit = 0.0
                discount = 0.0

                if move.sale_line_id:
                    price_unit = move.sale_line_id.price_unit
                    discount = move.sale_line_id.discount or 0.0
                else:
                    # Fallback sur le prix standard du produit
                    price_unit = move.product_id.list_price

                # Calcul avec remise
                price_after_discount = price_unit * (1 - discount / 100.0)
                line_total = qty * price_after_discount

                amount_untaxed += line_total

                # Calcul de la TVA
                if move.product_id.taxes_id:
                    tax_results = move.product_id.taxes_id.compute_all(
                        price_after_discount,
                        currency=picking.currency_id,
                        quantity=qty,
                        product=move.product_id,
                        partner=picking.partner_id
                    )
                    amount_tax += sum(tax['amount'] for tax in tax_results['taxes'])

            picking.amount_untaxed = amount_untaxed
            picking.amount_tax = amount_tax
            picking.amount_total = amount_untaxed + amount_tax

    def action_print_bl_safe(self):
        self.ensure_one()

        if self.state != 'done':
            raise UserError("Le bon de livraison ne peut être imprimé que lorsque la livraison est terminée.")

        if not self.delivery_note_number:
            raise UserError("Aucun numéro de bon de livraison généré. Veuillez d'abord générer le BL.")

        return self.env.ref('cpss_delivery_note_dz.action_report_delivery_note_original').report_action(self)

    def action_print_bl_ttc_safe(self):
        self.ensure_one()

        if self.state != 'done':
            raise UserError("Le bon de livraison TTC ne peut être imprimé que lorsque la livraison est terminée.")

        if not self.delivery_note_number:
            raise UserError("Aucun numéro de bon de livraison généré. Veuillez d'abord générer le BL.")

        return self.env.ref('cpss_delivery_note_dz.action_report_delivery_note_ttc').report_action(self)

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

                # Enregistrer la date de génération
                picking.delivery_note_date = fields.Datetime.now()

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


class StockMove(models.Model):
    _inherit = 'stock.move'

    # Champs pour le rapport (depuis la ligne de commande)
    price_unit = fields.Float(
        string='Prix Unitaire',
        compute='_compute_price_fields',
        store=True
    )

    discount = fields.Float(
        string='Remise (%)',
        compute='_compute_price_fields',
        store=True
    )

    price_subtotal = fields.Monetary(
        string='Sous-total',
        compute='_compute_price_fields',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='picking_id.currency_id',
        store=True
    )

    @api.depends('sale_line_id.price_unit', 'sale_line_id.discount', 'quantity_done', 'product_id.list_price')
    def _compute_price_fields(self):
        """Calcule les champs de prix depuis la ligne de commande"""
        for move in self:
            if move.sale_line_id:
                move.price_unit = move.sale_line_id.price_unit
                move.discount = move.sale_line_id.discount or 0.0
            else:
                move.price_unit = move.product_id.list_price
                move.discount = 0.0

            # Calcul du sous-total avec la quantité livrée
            qty = move.quantity_done if move.quantity_done else move.product_uom_qty
            price_after_discount = move.price_unit * (1 - move.discount / 100.0)
            move.price_subtotal = qty * price_after_discount