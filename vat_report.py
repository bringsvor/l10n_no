# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.report import report_sxw
from common_report_header import common_report_header

import time


class secret_tax_report(report_sxw.rml_parse, common_report_header):
    #def _get_account(self, data):
    #    assert False
    #def get_account(self, data):
    #    assert False
    #def _get_codes(self, data):
    #    assert False
    #def _get_general(self, data):
    #    assert False

    def __init__(self, cr, uid, name, context=None):
        print "INIT!"
        super(secret_tax_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_codes': self._get_codes,
            'get_general': self._get_general,
            'get_currency': self._get_currency,
            'get_lines': self._get_lines,
            'get_fiscalyear': self._get_fiscalyear,
            'get_account': self._get_account,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period,
            'get_basedon': self._get_basedon,
        })


    def _get_basedon(self, form):
        return form['form']['based_on']


    def set_context(self, objects, data, ids, report_type=None):
        new_ids = ids
        res = {}
        self.period_ids = []
        period_obj = self.pool.get('account.period')
        self.display_detail = data['form']['display_detail']
        res['periods'] = ''
        res['fiscalyear'] = data['form'].get('fiscalyear_id', False)

        if data['form'].get('period_from', False) and data['form'].get('period_to', False):
            self.period_ids = period_obj.build_ctx_periods(self.cr, self.uid, data['form']['period_from'], data['form']['period_to'])
            periods_l = period_obj.read(self.cr, self.uid, self.period_ids, ['name'])
            for period in periods_l:
                if res['periods'] == '':
                    res['periods'] = period['name']
                else:
                    res['periods'] += ", "+ period['name']
        return super(secret_tax_report, self).set_context(objects, data, new_ids, report_type=report_type)


    def _get_codes(self, based_on, company_id, parent=False, level=0, period_list=None, context=None):
        obj_tc = self.pool.get('account.tax.code')
        ids = obj_tc.search(self.cr, self.uid, [('parent_id','=',parent),('company_id','=',company_id)], order='sequence', context=context)

        res = []
        for code in obj_tc.browse(self.cr, self.uid, ids, {'based_on': based_on}):
            res.append(('.'*2*level, code))

            res += self._get_codes(based_on, company_id, code.id, level+1, context=context)
        return res


    def _get_general(self, tax_code_id, period_list, company_id, based_on, context=None):
        if not self.display_detail:
            return []
        res = []
        obj_account = self.pool.get('account.account')
        periods_ids = tuple(period_list)
        if based_on == 'payments':
            self.cr.execute('SELECT SUM(line.tax_amount) AS tax_amount, \
                        SUM(line.debit) AS debit, \
                        SUM(line.credit) AS credit, \
                        COUNT(*) AS count, \
                        account.id AS account_id, \
                        account.name AS name,  \
                        account.code AS code \
                    FROM account_move_line AS line, \
                        account_account AS account, \
                        account_move AS move \
                        LEFT JOIN account_invoice invoice ON \
                            (invoice.move_id = move.id) \
                    WHERE line.state<>%s \
                        AND line.tax_code_id = %s  \
                        AND line.account_id = account.id \
                        AND account.company_id = %s \
                        AND move.id = line.move_id \
                        AND line.period_id IN %s \
                        AND ((invoice.state = %s) \
                            OR (invoice.id IS NULL))  \
                    GROUP BY account.id,account.name,account.code', ('draft', tax_code_id,
                        company_id, periods_ids, 'paid',))

        else:
            self.cr.execute('SELECT SUM(line.tax_amount) AS tax_amount, \
                        SUM(line.debit) AS debit, \
                        SUM(line.credit) AS credit, \
                        COUNT(*) AS count, \
                        account.id AS account_id, \
                        account.name AS name,  \
                        account.code AS code \
                    FROM account_move_line AS line, \
                        account_account AS account \
                    WHERE line.state <> %s \
                        AND line.tax_code_id = %s  \
                        AND line.account_id = account.id \
                        AND account.company_id = %s \
                        AND line.period_id IN %s\
                        AND account.active \
                    GROUP BY account.id,account.name,account.code', ('draft', tax_code_id,
                        company_id, periods_ids,))
        res = self.cr.dictfetchall()

        i = 0
        while i<len(res):
            res[i]['account'] = obj_account.browse(self.cr, self.uid, res[i]['account_id'], context=context)
            i+=1
        return res

    codes = [
        (1, 'Samlet omsetning og uttak innenfor og utenfor mva.-loven'),
        (2, 'Samlet omsetning og uttak innenfor mva.-loven'),
        (3, 'Omsetning og uttak i post 2 som er fritatt for mva'),
        (4, 'Omsetning og uttak i post 2 med standard sats'),
        (5, 'Omsetning og uttak i post 2 med middels sats'),
        (6, 'Omsetning og uttak i post 2 med lav sats'),
        (7, 'Tjenester kjøpt fra utlandet, og beregnet avgift 25%'),
        (8, 'Fradragsberettiget inngående avgift, standard sats'),
        (9, 'Fradragsberettiget inngående avgift, middels sats'),
        (10, 'Fradragsberettiget inngående avgift, lav sats'),
        (11, 'Avgift å betale'),
        (11, 'Avgift til gode')
    ]
### Trur vi må bruke ir.property for å konfigurere dette, i alle fall felt 7.
    """

elmatica8-15=# select tax.name, tc.name, tax.type_tax_use from account_tax tax, account_tax_code tc where tax.base_code_id=tc.id;
          name           |          name           | type_tax_use
-------------------------+-------------------------+--------------
 Utgående 25% mva(25.0%) | Base of Taxed Sales     | sale
 Utgående 15% MVA        | Base of Taxed Sales     | sale
 Utgående 8% MVA         | Base of Taxed Sales     | sale
 Inngående 25% MVA       | Base of Taxed Purchases | purchase
 Inngående 15% MVA       | Base of Taxed Purchases | purchase
 Inngående 8% MVA        | Base of Taxed Purchases | purchase
(6 rows)
"""
    """

SELECT SUM(line.tax_amount) AS tax_amount,
                        SUM(line.debit) AS debit,
                        SUM(line.credit) AS credit,
                        COUNT(*) AS count,
                        account.id AS account_id,
                        account.name AS name,
                        account.code AS code,
                line.period_id, tax.name
                    FROM account_move_line AS line,
                        account_account AS account ,
account_tax_code as tax
                    WHERE line.state <> 'draft'
                    --    AND line.tax_code_id = %s
and line.tax_code_id=tax.id
                        AND line.account_id = account.id
                    --    AND account.company_id = %s
                    --    AND line.period_id IN %s
                        AND account.active
                    GROUP BY account.id,account.name,account.code, line.period_id, tax.name;



 tax_amount | debit | credit  | count | account_id |                     name                      | code | period_id |         name
------------+-------+---------+-------+------------+-----------------------------------------------+------+-----------+----------------------
      80.00 |  0.00 |   80.00 |     1 |        133 | Utgående merverdiavgift                       | 2700 |         9 | Tax Due (Tax to pay)
    1000.00 |  0.00 | 1000.00 |     1 |        162 | Salgsinntekt handelsvarer avgiftspl. høy sats | 3000 |         9 | Base of Taxed Sales
(2 rows)

"""



    def _get_lines(self, based_on, company_id=False, parent=False, level=0, context=None):
        lines = []
        for linetype in self.codes:
            res_dict = { 'code': linetype[0],
                'name': linetype[1],
                'tax_base': 10000,
                'tax_amount': 9299,
            }
            lines.append(res_dict)
        return lines



        period_list = self.period_ids
        res = self._get_codes(based_on, company_id, parent, level, period_list, context=context)
        if period_list:
            res = self._add_codes(based_on, res, period_list, context=context)
        else:
            self.cr.execute ("select id from account_fiscalyear")
            fy = self.cr.fetchall()
            self.cr.execute ("select id from account_period where fiscalyear_id = %s",(fy[0][0],))
            periods = self.cr.fetchall()
            for p in periods:
                period_list.append(p[0])
            res = self._add_codes(based_on, res, period_list, context=context)

        i = 0
        top_result = []
        while i < len(res):

            res_dict = { 'code': res[i][1].code,
                'name': res[i][1].name,
                'tax_base': 0,
                'tax_amount': res[i][1].sum_period,
                'type': 1,
                'level': res[i][0],
                'pos': 0
            }

            top_result.append(res_dict)
            res_general = self._get_general(res[i][1].id, period_list, company_id, based_on, context=context)
            ind_general = 0
            while ind_general < len(res_general):
                res_general[ind_general]['type'] = 2
                res_general[ind_general]['pos'] = 0
                res_general[ind_general]['level'] = res_dict['level']
                top_result.append(res_general[ind_general])
                ind_general+=1
            i+=1
        return top_result

    def _add_codes(self, based_on, account_list=None, period_list=None, context=None):
        if account_list is None:
            account_list = []
        if period_list is None:
            period_list = []
        res = []
        obj_tc = self.pool.get('account.tax.code')
        for account in account_list:
            ids = obj_tc.search(self.cr, self.uid, [('id','=', account[1].id)], context=context)
            sum_tax_add = 0
            for period_ind in period_list:
                for code in obj_tc.browse(self.cr, self.uid, ids, {'period_id':period_ind,'based_on': based_on}):
                    sum_tax_add = sum_tax_add + code.sum_period

            code.sum_period = sum_tax_add

            res.append((account[0], code))
        return res



class report_vat(osv.AbstractModel):
    _name = 'report.l10n_no.report_vat'
    _inherit = 'report.abstract_report'
    _template = 'l10n_no.report_vat'
    _wrapped_report_class = secret_tax_report

    def get_account(self):
        assert False

    def _get_account(self):
        assert False


#report_sxw.report_sxw('report.account.vat.declarationIII', 'account.tax.code',
#    'addons/account/report/account_tax_report.rml', parser=secret_tax_report, header="internal")


class l10n_no_vat_declaration(osv.osv_memory):
    _name = 'l10n_no.vat.declaration'
    _description = 'Account Vat Declaration'
    _inherit = "account.common.report"
    _columns = {
        'based_on': fields.selection([('invoices', 'Invoices'),
                                      ('payments', 'Payments'),],
                                      'Based on', required=True),
        'chart_tax_id': fields.many2one('account.tax.code', 'Chart of Tax', help='Select Charts of Taxes', required=True, domain = [('parent_id','=', False)]),
        'display_detail': fields.boolean('Display Detail'),
    }



    def _get_account(self):
        assert False

    def get_account(self):
        assert False

    def _get_tax(self, cr, uid, context=None):
        print "RETURNING TAXES"
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        taxes = self.pool.get('account.tax.code').search(cr, uid, [('parent_id', '=', False), ('company_id', '=', user.company_id.id)], limit=1)
        return taxes and taxes[0] or False

    _defaults = {
        'based_on': 'invoices',
        'chart_tax_id': _get_tax
    }

    def create_vat(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        datas = {'ids': context.get('active_ids', [])}
        # HADDE datas['model'] = 'account.tax.code'
        datas['model'] = 'l10n_no.vat_declaration'
        datas['form'] = self.read(cr, uid, ids, context=context)[0]

        for field in datas['form'].keys():
            if isinstance(datas['form'][field], tuple):
                datas['form'][field] = datas['form'][field][0]

        taxcode_obj = self.pool.get('account.tax.code')
        taxcode_id = datas['form']['chart_tax_id']
        taxcode = taxcode_obj.browse(cr, uid, [taxcode_id], context=context)[0]
        datas['form']['company_id'] = taxcode.company_id.id

        #report_name = 'l10n_no.account.vat.declarationIII'
        report_name = 'l10n_no.report_vat'
        #report_name = 'report.l10n_no.account.report_vat' # 'l10n_no.account.vat.declarationIII' # 'account.report_vat'
        return self.pool['report'].get_action(cr, uid, [], report_name, data=datas, context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:



##############3
class VatDeclarationReport(osv.AbstractModel):
    _name = 'report.vat_declaration_particular'

    def render_html(self, cr, uid, ids, data=None, context=None):
        assert False

