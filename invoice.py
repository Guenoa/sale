#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import Workflow, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['Invoice', 'InvoiceLine']
__metaclass__ = PoolMeta


class Invoice:
    __name__ = 'account.invoice'
    sales = fields.Many2Many('sale.sale-account.invoice',
            'invoice', 'sale', 'Sales', readonly=True)
    sale_exception_state = fields.Function(fields.Selection([
        ('', ''),
        ('ignored', 'Ignored'),
        ('recreated', 'Recreated'),
        ], 'Exception State'), 'get_sale_exception_state')

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        cls._error_messages.update({
            'delete_sale_invoice': 'You can not delete invoices '
                    'that come from a sale!',
            'reset_invoice_sale': 'You cannot reset to draft '
                    'an invoice generated by a sale.',
            })

    @classmethod
    def get_sale_exception_state(cls, invoices, name):
        Sale = Pool().get('sale.sale')
        sales = Sale.search([
                ('invoices', 'in', [i.id for i in invoices]),
                ])

        recreated = tuple(i for p in sales for i in p.invoices_recreated)
        ignored = tuple(i for p in sales for i in p.invoices_ignored)

        states = {}
        for invoice in invoices:
            states[invoice.id] = ''
            if invoice in recreated:
                states[invoice.id] = 'recreated'
            elif invoice.id in ignored:
                states[invoice.id] = 'ignored'
        return states

    def copy(self, ids, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default.setdefault('sales', None)
        return super(Invoice, self).copy(ids, default=default)

    @classmethod
    def delete(cls, invoices):
        if invoices:
            Transaction().cursor.execute('SELECT id FROM sale_invoices_rel '
                'WHERE invoice IN (' + ','.join(('%s',) * len(invoices)) + ')',
                [i.id for i in invoices])
            if Transaction().cursor.fetchone():
                cls.raise_user_error('delete_sale_invoice')
        super(Invoice, cls).delete(invoices)

    @classmethod
    def paid(cls, invoices):
        pool = Pool()
        Sale = pool.get('sale.sale')
        super(Invoice, cls).paid(invoices)
        Sale.process([s for i in invoices for s in i.sales])

    @classmethod
    def cancel(cls, invoices):
        pool = Pool()
        Sale = pool.get('sale.sale')
        super(Invoice, cls).cancel(invoices)
        Sale.process([s for i in invoices for s in i.sales])

    @classmethod
    @Workflow.transition('draft')
    def draft(cls, invoices):
        Sale = Pool().get('sale.sale')
        sales = Sale.search([
                ('invoices', 'in', [i.id for i in invoices]),
                ])

        if sales:
            cls.raise_user_error('reset_invoice_sale')

        return super(Invoice, cls).draft(invoices)


class InvoiceLine:
    __name__ = 'account.invoice.line'
    sale_lines = fields.Many2Many('sale.line-account.invoice.line',
            'invoice_line', 'sale_line', 'Sale Lines', readonly=True)

    @classmethod
    def copy(cls, lines, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default.setdefault('sale_lines', None)
        return super(InvoiceLine, cls).copy(lines, default=default)
