# -*- coding: utf-8 -*-
from odoo import fields, models


class PeEdiLog(models.Model):
    _name = 'pe.edi.log'
    _description = 'Registro técnico SUNAT'
    _order = 'id desc'

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    operation = fields.Selection([
        ('generate', 'Generación XML'),
        ('send', 'Envío'),
        ('status', 'Consulta de estado'),
        ('cancel', 'Comunicación de baja'),
        ('gre', 'Guía de Remisión'),
    ], required=True)
    success = fields.Boolean()
    message = fields.Text()

    def create_log(self, record, operation, success, message):
        return self.sudo().create({
            'company_id': record.company_id.id if 'company_id' in record._fields else self.env.company.id,
            'res_model': record._name,
            'res_id': record.id,
            'operation': operation,
            'success': success,
            'message': message,
        })
