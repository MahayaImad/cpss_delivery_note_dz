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

    # Champs calculés pour les totaux (utilisés dans le rapport)
    amount_untaxed = fields.Monetary(
        string='Montant HT',
        currency_field='currency_id',
        default=0.0
    )

    amount_tax = fields.Monetary(
        string='TVA',
        currency_field='currency_id',
        default=0.0
    )

    amount_total = fields.Monetary(
        string='Total TTC',
        currency_field='currency_id',
        default=0.0
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
        string='État Facturation',
        store=True,
    )

    sale_payment_state = fields.Selection(
        related='sale_id.invoice_status',
        string='État Paiement',
        store=True,
    )

    # Champs pour les conditions d'affichage dans la vue
    location_src_usage = fields.Selection(
        related='location_id.usage',
        string='Source Location Usage',
        store=True,
        readonly=True
    )

    location_dest_usage = fields.Selection(
        related='location_dest_id.usage',
        string='Destination Location Usage',
        store=True,
        readonly=True
    )

    # Champs calculés pour l'affichage dynamique des boutons
    document_title_display = fields.Char(
        string='Titre du Document',
        compute='_compute_document_titles',
        help="Titre dynamique du document basé sur le type d'opération"
    )

    document_title_ttc_display = fields.Char(
        string='Titre du Document TTC',
        compute='_compute_document_titles',
        help="Titre dynamique du document TTC"
    )

    @api.depends('picking_type_code', 'location_src_usage', 'location_dest_usage', 'state')
    def _compute_document_titles(self):
        """Calcule les titres dynamiques pour les boutons"""
        for picking in self:
            # Titre de base
            base_title = picking._get_document_title_for_report()
            picking.document_title_display = base_title

            # Titre TTC
            if "LIVRAISON" in base_title:
                picking.document_title_ttc_display = base_title.replace("LIVRAISON", "LIVRAISON TTC")
            elif "RETOUR" in base_title:
                picking.document_title_ttc_display = base_title + " TTC"
            elif "RÉCEPTION" in base_title:
                picking.document_title_ttc_display = base_title + " TTC"
            else:
                picking.document_title_ttc_display = base_title + " TTC"

    def action_print_bl_dynamic(self):
        """Imprimer BL avec titre dynamique"""
        self.ensure_one()

        if self.state != 'done':
            raise UserError("Le document ne peut être imprimé que lorsque l'opération est terminée.")

        # Titre dynamique pour notification
        document_title = self._get_document_title_for_report()

        # Message de confirmation
        message = f"Impression du {document_title} en cours..."
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Impression',
                'message': message,
                'type': 'success',
                'next': self.env.ref('cpss_delivery_note_dz.action_report_delivery_note').report_action(self)
            }
        }

    def action_print_bl_ttc_dynamic(self):
        """Imprimer BL TTC avec titre dynamique"""
        self.ensure_one()

        if self.state != 'done':
            raise UserError("Le document TTC ne peut être imprimé que lorsque l'opération est terminée.")

        if self.picking_type_code != 'outgoing':
            raise UserError("Le rapport TTC n'est disponible que pour les opérations sortantes.")

        # Titre dynamique TTC
        base_title = self._get_document_title_for_report()
        if "LIVRAISON" in base_title:
            ttc_title = base_title.replace("LIVRAISON", "LIVRAISON TTC")
        elif "RETOUR" in base_title:
            ttc_title = base_title + " TTC"
        else:
            ttc_title = base_title + " TTC"

        # Message de confirmation
        message = f"Impression du {ttc_title} en cours..."
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Impression TTC',
                'message': message,
                'type': 'success',
                'next': self.env.ref('cpss_delivery_note_dz.action_report_delivery_note_ttc').report_action(self)
            }
        }

    def _get_operation_type_name(self):
        """Retourne le nom du type d'opération en français"""
        operation_names = {
            'incoming': 'Réception',
            'outgoing': 'Livraison',
            'internal': 'Transfert Interne',
        }

        # Cas spéciaux pour les retours
        if self.location_id.usage == 'customer' and self.location_dest_id.usage == 'internal':
            return 'Retour Client'
        elif self.location_id.usage == 'internal' and self.location_dest_id.usage == 'supplier':
            return 'Retour Fournisseur'

        return operation_names.get(self.picking_type_code, 'Document')

    def _get_dynamic_report_name(self):
        """Génère le nom du rapport basé sur le type d'opération"""
        self.ensure_one()

        operation_name = self._get_operation_type_name()
        partner_name = self.partner_id.name or 'Inconnu'

        # Format : "Type Opération - Partenaire - Référence"
        return f"{operation_name} - {partner_name} - {self.name}"

    def _get_bl_report_name(self):
        """Génère le nom du BL selon le type d'opération"""
        self.ensure_one()

        if self.picking_type_code == 'outgoing':
            if self.location_id.usage == 'internal' and self.location_dest_id.usage == 'customer':
                return f"BL Livraison - {self.name}"
            else:
                return f"BL Sortie - {self.name}"

        elif self.picking_type_code == 'incoming':
            if self.location_id.usage == 'customer' and self.location_dest_id.usage == 'internal':
                return f"BL Retour Client - {self.name}"
            else:
                return f"BL Réception - {self.name}"

        elif self.picking_type_code == 'internal':
            return f"BL Transfert - {self.name}"

        else:
            return f"BL - {self.name}"

    def _get_bl_ttc_report_name(self):
        """Génère le nom du BL TTC selon le type d'opération"""
        self.ensure_one()

        base_name = self._get_bl_report_name()
        return base_name.replace('BL', 'BL TTC')

    def _get_document_title_for_report(self):
        """Retourne le titre du document pour l'affichage dans le rapport"""
        self.ensure_one()

        # 1. RETOUR CLIENT (incoming : customer -> internal)
        if (self.picking_type_code == 'incoming' and
                self.location_id.usage == 'customer' and
                self.location_dest_id.usage == 'internal'):
            return 'BON DE RETOUR CLIENT'

        # 2. RETOUR FOURNISSEUR (outgoing : internal -> supplier)
        elif (self.picking_type_code == 'outgoing' and
              self.location_id.usage == 'internal' and
              self.location_dest_id.usage == 'supplier'):
            return 'BON DE RETOUR FOURNISSEUR'

        # 3. LIVRAISON NORMALE (outgoing : internal -> customer)
        elif (self.picking_type_code == 'outgoing' and
              self.location_id.usage == 'internal' and
              self.location_dest_id.usage == 'customer'):
            return 'BON DE LIVRAISON'

        # 4. RÉCEPTION NORMALE (incoming : supplier -> internal)
        elif (self.picking_type_code == 'incoming' and
              self.location_id.usage == 'supplier' and
              self.location_dest_id.usage == 'internal'):
            return 'BON DE RÉCEPTION'

        # 5. TRANSFERT INTERNE
        elif (self.picking_type_code == 'internal' and
              self.location_id.usage == 'internal' and
              self.location_dest_id.usage == 'internal'):
            return 'BON DE TRANSFERT'

        # 6. CAS GÉNÉRIQUES (fallback basé sur picking_type_code)
        elif self.picking_type_code == 'outgoing':
            return 'BON DE SORTIE'
        elif self.picking_type_code == 'incoming':
            return 'BON D\'ENTRÉE'
        elif self.picking_type_code == 'internal':
            return 'BON DE TRANSFERT'

        # 7. FALLBACK ULTIME
        return 'DOCUMENT LOGISTIQUE'

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

    def _compute_financial_amounts(self):
        """Calcule les montants sans @api.depends"""
        amount_untaxed = 0.0
        amount_tax = 0.0

        for move in self.move_ids_without_package:
            if move.state == 'cancel':
                continue
            qty = move.quantity_done or move.product_uom_qty

            # CORRECTION : Gérer vente ET achat
            price_unit = 0.0
            discount = 0.0
            taxes = False

            if move.sale_line_id:  # Commande de vente
                price_unit = move.sale_line_id.price_unit
                discount = move.sale_line_id.discount or 0.0
                taxes = move.sale_line_id.tax_id
            elif move.purchase_line_id:  # Commande d'achat
                price_unit = move.purchase_line_id.price_unit
                discount = move.purchase_line_id.discount or 0.0
                taxes = move.purchase_line_id.taxes_id
            else:  # Fallback
                price_unit = move.product_id.list_price
                taxes = move.product_id.taxes_id

            price_after_discount = price_unit * (1 - discount / 100.0)
            line_total = qty * price_after_discount
            amount_untaxed += line_total

            # Calcul de la TVA avec les bonnes taxes
            if taxes:
                tax_results = taxes.compute_all(
                    price_after_discount, self.currency_id, qty, move.product_id, self.partner_id
                )
                amount_tax += sum(tax['amount'] for tax in tax_results['taxes'])

        self.write({
            'amount_untaxed': amount_untaxed,
            'amount_tax': amount_tax,
            'amount_total': amount_untaxed + amount_tax,
        })

    @api.depends('move_ids_without_package.price_unit', 'move_ids_without_package.quantity_done',
                 'move_ids_without_package.product_id.taxes_id', 'move_ids_without_package.sale_line_id',
                 'move_ids_without_package.purchase_line_id')
    def _compute_amounts(self):
        """Calcule les montants basés sur les quantités livrées"""
        for picking in self:
            amount_untaxed = 0.0
            amount_tax = 0.0

            for move in picking.move_ids_without_package:
                if move.state == 'cancel':
                    continue

                qty = move.quantity_done if move.quantity_done else move.product_uom_qty
                price_unit = 0.0
                discount = 0.0
                taxes = False

                # CORRECTION : Gérer vente ET achat
                if move.sale_line_id:
                    price_unit = move.sale_line_id.price_unit
                    discount = move.sale_line_id.discount or 0.0
                    taxes = move.sale_line_id.tax_id
                elif move.purchase_line_id:
                    price_unit = move.purchase_line_id.price_unit
                    discount = move.purchase_line_id.discount or 0.0
                    taxes = move.purchase_line_id.taxes_id
                else:
                    price_unit = move.product_id.list_price
                    taxes = move.product_id.taxes_id

                price_after_discount = price_unit * (1 - discount / 100.0)
                line_total = qty * price_after_discount
                amount_untaxed += line_total

                # Calcul de la TVA avec les bonnes taxes
                if taxes:
                    tax_results = taxes.compute_all(
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

    # ======================================
    # CHAMPS POUR LES VUES ÉTENDUES
    # ======================================

    # Champs pour les achats
    purchase_id = fields.Many2one(
        'purchase.order',
        string='Commande d\'Achat',
        compute='_compute_purchase_fields',
        store=True
    )

    purchase_invoice_status = fields.Selection(
        related='purchase_id.invoice_status',
        string='État Facturation Achat',
        store=True
    )

    purchase_user_id = fields.Many2one(
        related='purchase_id.user_id',
        string='Responsable Achat',
        store=True
    )

    # Montants calculés avec gestion des retours en négatif
    amount_untaxed_computed = fields.Monetary(
        string='Montant HT (Calculé)',
        compute='_compute_amounts_with_sign',
        store=True,
        currency_field='currency_id'
    )

    amount_tax_computed = fields.Monetary(
        string='TVA (Calculée)',
        compute='_compute_amounts_with_sign',
        store=True,
        currency_field='currency_id'
    )

    amount_total_computed = fields.Monetary(
        string='Total TTC (Calculé)',
        compute='_compute_amounts_with_sign',
        store=True,
        currency_field='currency_id'
    )

    # Type d'opération pour les filtres
    operation_type = fields.Selection([
        ('livraison_client', 'Livraison Client'),
        ('retour_client', 'Retour Client'),
        ('reception_fournisseur', 'Réception Fournisseur'),
        ('retour_fournisseur', 'Retour Fournisseur'),
        ('transfert_interne', 'Transfert Interne'),
        ('autre', 'Autre'),
    ], string='Type d\'Opération', compute='_compute_operation_type', store=True)

    @api.depends('move_ids', 'purchase_id')
    def _compute_purchase_fields(self):
        """Calcule les champs liés aux achats"""
        for picking in self:
            purchase_order = False

            # Méthode 1: Depuis les move_ids
            if picking.move_ids:
                purchase_lines = picking.move_ids.mapped('purchase_line_id')
                if purchase_lines:
                    purchase_order = purchase_lines[0].order_id

            # Méthode 2: Depuis l'origine
            if not purchase_order and picking.origin:
                purchase_order = self.env['purchase.order'].search([
                    ('name', '=', picking.origin)
                ], limit=1)

            picking.purchase_id = purchase_order

    @api.depends('picking_type_code', 'location_src_usage', 'location_dest_usage')
    def _compute_operation_type(self):
        """Calcule le type d'opération standardisé"""
        for picking in self:
            if (picking.picking_type_code == 'outgoing' and
                    picking.location_src_usage == 'internal' and
                    picking.location_dest_usage == 'customer'):
                picking.operation_type = 'livraison_client'

            elif (picking.picking_type_code == 'incoming' and
                  picking.location_src_usage == 'customer' and
                  picking.location_dest_usage == 'internal'):
                picking.operation_type = 'retour_client'

            elif (picking.picking_type_code == 'incoming' and
                  picking.location_src_usage == 'supplier' and
                  picking.location_dest_usage == 'internal'):
                picking.operation_type = 'reception_fournisseur'

            elif (picking.picking_type_code == 'outgoing' and
                  picking.location_src_usage == 'internal' and
                  picking.location_dest_usage == 'supplier'):
                picking.operation_type = 'retour_fournisseur'

            elif (picking.picking_type_code == 'internal' and
                  picking.location_src_usage == 'internal' and
                  picking.location_dest_usage == 'internal'):
                picking.operation_type = 'transfert_interne'

            else:
                picking.operation_type = 'autre'

    @api.depends('amount_untaxed', 'amount_tax', 'amount_total', 'operation_type')
    def _compute_amounts_with_sign(self):
        """Calcule les montants avec signe selon le type d'opération"""
        for picking in self:
            # Les retours sont comptés en négatif
            sign = 1
            if picking.operation_type in ['retour_client', 'retour_fournisseur']:
                sign = -1

            picking.amount_untaxed_computed = picking.amount_untaxed * sign
            picking.amount_tax_computed = picking.amount_tax * sign
            picking.amount_total_computed = picking.amount_total * sign

    # ======================================
    # MÉTHODES POUR LES RAPPORTS FINANCIERS
    # ======================================

    @api.model
    def get_bl_vente_summary(self, date_from=False, date_to=False):
        """Résumé financier des BL Vente"""
        domain = [
            ('operation_type', 'in', ['livraison_client', 'retour_client']),
            ('state', '=', 'done')
        ]

        if date_from:
            domain.append(('date_done', '>=', date_from))
        if date_to:
            domain.append(('date_done', '<=', date_to))

        pickings = self.search(domain)

        return {
            'total_count': len(pickings),
            'livraisons_count': len(pickings.filtered(lambda p: p.operation_type == 'livraison_client')),
            'retours_count': len(pickings.filtered(lambda p: p.operation_type == 'retour_client')),
            'total_ht': sum(pickings.mapped('amount_untaxed_computed')),
            'total_tva': sum(pickings.mapped('amount_tax_computed')),
            'total_ttc': sum(pickings.mapped('amount_total_computed')),
            'to_invoice_count': len(pickings.filtered(lambda p: p.sale_invoice_status == 'to invoice')),
            'invoiced_count': len(pickings.filtered(lambda p: p.sale_invoice_status == 'invoiced')),
        }

    @api.model
    def get_br_achat_summary(self, date_from=False, date_to=False):
        """Résumé financier des BR Achat"""
        domain = [
            ('operation_type', 'in', ['reception_fournisseur', 'retour_fournisseur']),
            ('state', '=', 'done')
        ]

        if date_from:
            domain.append(('date_done', '>=', date_from))
        if date_to:
            domain.append(('date_done', '<=', date_to))

        pickings = self.search(domain)

        return {
            'total_count': len(pickings),
            'receptions_count': len(pickings.filtered(lambda p: p.operation_type == 'reception_fournisseur')),
            'retours_count': len(pickings.filtered(lambda p: p.operation_type == 'retour_fournisseur')),
            'total_ht': sum(pickings.mapped('amount_untaxed_computed')),
            'total_tva': sum(pickings.mapped('amount_tax_computed')),
            'total_ttc': sum(pickings.mapped('amount_total_computed')),
            'to_invoice_count': len(pickings.filtered(lambda p: p.purchase_invoice_status == 'to invoice')),
            'invoiced_count': len(pickings.filtered(lambda p: p.purchase_invoice_status == 'invoiced')),
        }

    # ======================================
    # ACTIONS RAPIDES DEPUIS LES VUES
    # ======================================

    def action_view_sale_order(self):
        """Ouvre la commande de vente liée"""
        self.ensure_one()
        if not self.sale_id:
            return False

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_id.id,
            'target': 'current',
        }

    def action_view_purchase_order(self):
        """Ouvre la commande d'achat liée"""
        self.ensure_one()
        if not self.purchase_id:
            return False

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_id.id,
            'target': 'current',
        }

    def action_view_invoices(self):
        """Ouvre les factures liées"""
        self.ensure_one()

        if self.sale_id:
            invoices = self.sale_id.invoice_ids
            model = 'account.move'
        elif self.purchase_id:
            invoices = self.purchase_id.invoice_ids
            model = 'account.move'
        else:
            return False

        if not invoices:
            return False

        action = {
            'type': 'ir.actions.act_window',
            'res_model': model,
            'target': 'current',
        }

        if len(invoices) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': invoices.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', invoices.ids)],
                'name': _('Factures liées'),
            })

        return action

    # ======================================
    # SURCHARGE POUR CALCUL AUTO DES MONTANTS
    # ======================================

    def button_validate(self):
        """Override pour calculer les montants après validation"""
        res = super().button_validate()

        for picking in self:
            if picking.state == 'done':
                # Forcer le recalcul des montants
                picking._compute_financial_amounts()

                # Forcer le recalcul des champs calculés
                picking._compute_amounts_with_sign()

        return res



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
            elif move.purchase_line_id:
                move.price_unit = move.purchase_line_id.price_unit
                # Les commandes d'achat n'ont pas de champ discount par défaut
                move.discount = 0.0
            else:
                move.price_unit = move.product_id.list_price
                move.discount = 0.0

            # Calcul du sous-total avec la quantité livrée
            qty = move.quantity_done if move.quantity_done else move.product_uom_qty
            price_after_discount = move.price_unit * (1 - move.discount / 100.0)
            move.price_subtotal = qty * price_after_discount