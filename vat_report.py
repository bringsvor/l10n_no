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

import logging
from openerp.osv import fields, osv
from openerp.report import report_sxw
from docutils.parsers.rst.directives import percentage
from account_tax_code import TAX_REPORT_STRINGS
from common_report_header import common_report_header

import time

_logger = logging.getLogger(__name__)

class secret_tax_report(report_sxw.rml_parse, common_report_header):
    #def _get_account(self, data):
    #    assert False
    #def get_account(self, data):
    #    assert False
    #def _get_codes(self, data):
    #    assert False
    #def _get_general(self, data):
    #    assert False


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


    def __init__(self, cr, uid, name, context=None):
        print "INIT!"
        super(secret_tax_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_codes': self._get_codes,
            'get_general': self._get_general,
            'get_currency': self._get_currency,
            'get_reporting_currency': self._get_reporting_currency,
            'get_lines': self._get_lines,
            'get_fiscalyear': self._get_fiscalyear,
            'get_account': self._get_account,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period,
            'get_basedon': self._get_basedon,
        })

    def _get_basedon(self, form):
        return form['form']['based_on']


    def _get_reporting_currency(self, form):
        company_id = form['form']['company_id']
        rep = self.pool.get('res.company').browse(self.cr, self.uid, company_id).reporting_currency_id
        return rep.name

    def _get_lines(self, data, based_on, company_id=False, context=None):
        self.cr.execute("""select tc.id, tc.position_in_tax_report, tc.name, tax1.id as base, tax2.id as pay
        from account_tax_code tc
        left outer join account_tax tax1 on tax1.base_code_id=tc.id
        left outer join account_tax tax2 on tax2.tax_code_id=tc.id
        where (tax1.id is not null or tax2.id is not null)
        and tc.company_id=%(company_id)d and tc.position_in_tax_report is not null""" %
                        {'company_id' : company_id}
        )
        res = self.cr.dictfetchall()
        codes = {}

        line_names = [
        [1, 'Samlet omsetning og uttak innenfor og utenfor mva.-loven', 0.0, None],
        [2, 'Samlet omsetning og uttak innenfor mva.-loven', 0.0, None],
        [3, 'Omsetning og uttak i post 2 som er fritatt for mva', 0.0, 0.0],
        [4, 'Omsetning og uttak i post 2 med standard sats', 0.0, 0.0],
        [5, 'Omsetning og uttak i post 2 med middels sats', 0.0, 0.0],
        [6, 'Omsetning og uttak i post 2 med lav sats', 0.0, 0.0],
        [7, 'Tjenester kjøpt fra utlandet, og beregnet avgift 25%', 0.0, 0.0],
        [8, 'Fradragsberettiget inngående avgift, standard sats', 0.0, 0.0],
        [9, 'Fradragsberettiget inngående avgift, middels sats', 0.0, 0.0],
        [10, 'Fradragsberettiget inngående avgift, lav sats', 0.0, 0.0],
        [11, 'Avgift å betale', None, 0.0],
        [11, 'Avgift til gode', None, 0.0],
        ]


        for row in res:
            codes[row['id']] = row

        period_list = []

        form = data['form']
        fiscal_year = form['fiscalyear_id']
        start_period = form['period_from']
        period_list.append(start_period) # Hack
        if form['period_from']:
            period_id = form['period_from']
            period_list.append(period_id)
        else:
            self.cr.execute ("select id from account_period where fiscalyear_id = %d" % (fiscal_year))
            periods = self.cr.fetchall()
            for p in periods:
                period_list.append(p[0])


        query = """SELECT line.tax_code_id, tc.name, tc.position_in_tax_report,
                sum(abs(line.tax_amount)) , sum(abs(line.tax_amount_in_reporting_currency)) as tax_amt_reporting
                    FROM account_move_line  line,
                    account_move AS move ,
                        account_tax_code AS tc
                WHERE 1=1
--                    --WHERE line.tax_code_id IN %s '+where+'
                   AND move.id = line.move_id
                AND tc.id=line.tax_code_id
                AND line.company_id=%(company_id)d
                AND line.period_id IN (%(periods)s)
            --join account_tax_code tc on tc.id=line.tax_code_id
            GROUP BY line.tax_code_id, tc.name, tc.position_in_tax_report""" % {'company_id' : company_id,
                                                                                'periods' : ','.join(['%d' % x for x in period_list])}

        sum_all = 0.0
        sum_applied = 0.0
        to_pay = 0.0
        print "QUERY", query
        self.cr.execute(query)
        res = self.cr.dictfetchall()
        for row in res:
            amount_reporting = round(row['tax_amt_reporting'], 0)
            the_code = row['tax_code_id']
            codeinfo = codes.get(the_code)
            if not codeinfo:
                assert amount_reporting == 0.0, 'The amount_reporting is %.2f but we have no codeinfo for taxcode id %d - %s' % (amount_reporting, the_code, codes.keys())
                continue
            assert codeinfo
            _logger.info('Found codeinfo for tax %d : %s', the_code, codeinfo)
            position = codeinfo['position_in_tax_report']
            print "ROW", row
            print "CODEINFO", codeinfo
            assert codeinfo['base'] or codeinfo['pay']
            assert not (codeinfo['base'] and codeinfo['pay'])
            if codeinfo['base']:
                # Grunnlag
                if position in (3,4,5,6,7):
                    sum_all += amount_reporting
                if position in (4,5,6,7):
                    sum_applied += amount_reporting
                assert line_names[position-1][2] == 0.0
                line_names[position-1][2] = amount_reporting
            else:
                if position in (7,8,9,10):
                    sign = -1
                else:
                    sign = 1

                to_pay += sign * amount_reporting

                assert line_names[position-1][3] == 0.0
                line_names[position-1][3] = amount_reporting

        line_names[0][2] = sum_all
        line_names[1][2] = sum_applied
        if to_pay > 0:
            line_names[10][3] = to_pay
        else:
            line_names[11][3] = abs(to_pay)


        res = []
        for line in line_names:
            li = {'code' : line[0],
                  'name' : line[1],
                  'tax_base_reporting' : line[2],
                  'tax_amount_reporting' : line[3]}
            res.append(li)
        return res



    def X_get_lines(self, based_on, company_id=False, parent=False, level=0, context=None):
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
                'debit': 0,
                'credit': 0,
                'tax_base' : 0,
                'tax_amount': res[i][1].sum_period,
                'tax_amount_reporting' : res[i][1].sum_period,
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
            res[i]['tax_base'] = 99.0
            i+=1
        return res

    def _get_codes(self, based_on, company_id, parent=False, level=0, period_list=[], context=None):
        obj_tc = self.pool.get('account.tax.code')
        ids = obj_tc.search(self.cr, self.uid, [('parent_id','=',parent),('company_id','=',company_id)], order='sequence', context=context)

        res = []
        for code in obj_tc.browse(self.cr, self.uid, ids, {'based_on': based_on}):
            res.append(('.'*2*level, code))

            res += self._get_codes(based_on, company_id, code.id, level+1, context=context)
        return res

    def _add_codes(self, based_on, account_list=[], period_list=[], context=None):
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

    def _get_currency(self, form, context=None):
        return self.pool.get('res.company').browse(self.cr, self.uid, form['company_id'], context=context).currency_id.name

    def sort_result(self, accounts, context=None):
        # On boucle sur notre rapport
        result_accounts = []
        ind=0
        old_level=0
        while ind<len(accounts):
            #
            account_elem = accounts[ind]
            #

            #
            # we will now check if the level is lower than the previous level, in this case we will make a subtotal
            if (account_elem['level'] < old_level):
                bcl_current_level = old_level
                bcl_rup_ind = ind - 1

                while (bcl_current_level >= int(accounts[bcl_rup_ind]['level']) and bcl_rup_ind >= 0 ):
                    res_tot = { 'code': accounts[bcl_rup_ind]['code'],
                        'name': '',
                        'debit': 0,
                        'credit': 0,
                        'tax_amount': accounts[bcl_rup_ind]['tax_amount'],
                        'tax_amount_reporting': accounts[bcl_rup_ind]['tax_amount'],
                        'type': accounts[bcl_rup_ind]['type'],
                        'level': 0,
                        'pos': 0
                    }

                    if res_tot['type'] == 1:
                        # on change le type pour afficher le total
                        res_tot['type'] = 2
                        result_accounts.append(res_tot)
                    bcl_current_level =  accounts[bcl_rup_ind]['level']
                    bcl_rup_ind -= 1

            old_level = account_elem['level']
            result_accounts.append(account_elem)
            ind+=1

        return result_accounts




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
        # The sum code
        res_dict = {'code' : 1,
                        'name' : TAX_REPORT_STRINGS[1],
                        'tax_base' : total_amount,
                        'tax_amount' : None,
                        'tax_base_reporting' : total_amount_reporting,
                        'tax_amount_reporting' : None,
                        'percentage' : None,
                        'tax_use' : None}
        lines.insert(0, res_dict)

        res_dict = {'code' : 2,
                        'name' : TAX_REPORT_STRINGS[2],
                        'tax_base' : total_amount_vatable,
                        'tax_amount' : None,
                        'tax_base_reporting' : total_amount_vatable_reporting,
                        'tax_amount_reporting' : None,
                        'percentage' : None,
                        'tax_use' : None}
        lines.insert(1, res_dict)


        if tax_to_pay > 0.0:
            name = TAX_REPORT_STRINGS[11][0]
        else:
            name = TAX_REPORT_STRINGS[11][1]

        res_dict = {'code' : 11,
                        'name' : name,
                        'tax_base' : None,
                        'tax_amount' : abs(tax_to_pay),
                        'tax_base_reporting' : None,
                        'tax_amount_reporting' : abs(tax_to_pay_reporting),
                        'percentage' : None,
                        'tax_use' : None}
        lines.append(res_dict)


        # Check that all are there




        return lines

"""




class report_vat(osv.AbstractModel):
    _name = 'report.l10n_no_vatreport.report_vat'
    _inherit = 'report.abstract_report'
    _template = 'l10n_no_vatreport.report_vat'
    _wrapped_report_class = secret_tax_report

    def get_account(self):
        assert False

    def _get_account(self):
        assert False


#report_sxw.report_sxw('report.account.vat.declarationIII', 'account.tax.code',
#    'addons/account/report/account_tax_report.rml', parser=secret_tax_report, header="internal")


class l10n_no_vat_declaration(osv.osv_memory):
    _name = 'l10n_no_vatreport.vat.declaration'
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
        report_name = 'l10n_no_vatreport.report_vat'
        #report_name = 'report.l10n_no.account.report_vat' # 'l10n_no.account.vat.declarationIII' # 'account.report_vat'
        return self.pool['report'].get_action(cr, uid, [], report_name, data=datas, context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:



##############3
class VatDeclarationReport(osv.AbstractModel):
    _name = 'report.vat_declaration_particular'

    def render_html(self, cr, uid, ids, data=None, context=None):
        assert False
