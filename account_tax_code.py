#-.- encoding: utf-8 -.-
__author__ = 'tbri'

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp

TAX_REPORT_STRINGS = [
    '', # dummy
    'Post 1 - Samlet omsetning og uttak innenfor og utenfor mva.-loven',
    'Post 2 - Samlet omsetning og uttak innenfor mva.-loven',
    'Post 3 - Omsetning og uttak i post 2 som er fritatt for mva.',
    'Post 4 - Omsetning og uttak i post 2 med standard sats',
    'Post 5 - Omsetning og uttak i post 2 med middels sats',
    'Post 6 - Omsetning og uttak i post 2 med lav sats',
    'Post 7 - Tjenester kjøpt fra utlandet, og beregnet avgift 25%',
    'Post 8 - Fradragsberettiget inngående avgift, standard sats',
    'Post 9 - Fradragsberettiget inngående avgift, middels sats',
    'Post 10 - Fradragsberettiget inngående avgift, lav sats',
    ('Post 11 - Avgift å betale', 'Post 11 - Avgift til gode'),
]

TAX_REPORT_SELECTION = [
    (3, TAX_REPORT_STRINGS[3]),
    (4,TAX_REPORT_STRINGS[4]),
    (5,TAX_REPORT_STRINGS[5]),
    (6,TAX_REPORT_STRINGS[6]),
    (7,TAX_REPORT_STRINGS[7]),

    (8,TAX_REPORT_STRINGS[8]),
    (9,TAX_REPORT_STRINGS[9]),
    (10,TAX_REPORT_STRINGS[10]),
]

class account_tax_code(models.Model):
    _inherit = ['account.tax.code']

    position_in_tax_report = fields.Selection(TAX_REPORT_SELECTION,
                                              string = 'Field (post) in tax report')
    tax_exempt = fields.Boolean('Tax exempt')


class account_tax_code_template(models.Model):
    """ Add fields used to layout VAT declaration """
    _inherit = 'account.tax.code.template'

    position_in_tax_report = fields.Selection(TAX_REPORT_SELECTION,
                                              string = 'Field (post) in tax report')
    tax_exempt = fields.Boolean('Tax exempt')
