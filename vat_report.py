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
from docutils.parsers.rst.directives import percentage
from account_tax_code import TAX_REPORT_STRINGS
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

    def _get_amount(self, tax_code_id, period_list, company_id, based_on, context):
        print "GET AMOUNT", tax_code_id
        period_ids = tuple(period_list)
        if based_on == 'payments':
            assert False
        else:
            self.cr.execute("""SELECT SUM(line.tax_amount) AS tax_amount,
                SUM(line.debit) AS debit,
                SUM(line.credit) AS credit,
                sum(line.tax_amount_in_reporting_currency) as tax_amount_reporting,
                sum(line.debit_in_reporting_currency) as debit_reporting,
                sum(line.credit_in_reporting_currency) as credit_reporting,
                COUNT(*) AS count,
                account.id AS account_id,
                account.name AS name,
                account.code AS code
                FROM account_move_line AS line,
                    account_account AS account
                WHERE line.state <> %s
                    AND line.tax_code_id = %s
                    AND line.account_id = account.id
                    AND account.company_id = %s
                    AND line.period_id IN %s
                    AND account.active
                GROUP BY account.id,account.name,account.code""", ('draft', tax_code_id,
                        company_id, period_ids,))
            res = self.cr.dictfetchall()

            print "VALUES RETURNED", res
            #assert len(res) < 2
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

    def _get_total_turnover(self, cr, uid):
        return 0


    codes = [
        (1, 'Samlet omsetning og uttak innenfor og utenfor mva.-loven', _get_total_turnover),
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

    def get_sign(self, signs, taxcode_id):
        result = 1.0
        if signs[taxcode_id][0]:
            result = result * self.get_sign(signs, signs[taxcode_id][0])

        return result * signs[taxcode_id][1]



    def _get_lines(self, based_on, company_id=False, parent=False, level=0, context=None):

        self.cr.execute('select id, parent_id, sign, tax_exempt from account_tax_code')
        basecodes = self.cr.dictfetchall()
        signs = {}
        exempt = set()
        for bc in basecodes:
            signs[bc['id']] = (bc['parent_id'], bc['sign'])
            if bc['tax_exempt']:
                exempt.add(bc['id'])
        print "EXEMPT LIST", exempt

        lines = []

        self.cr.execute('select tax.id as tax_id, tax.name as tax_name, tax.type_tax_use as tax_type, tax.amount as tax_amount,'
                            ' tax.ref_base_code_id, tax.ref_tax_code_id, tax.base_code_id, tax.tax_code_id'
                            ' from account_tax tax')
        taxcodes = self.cr.dictfetchall()
        bases = set()
        taxes = set()
        purchases = set()
        percentages = {}

        for tax in taxcodes:
            percentages[tax['tax_id']] = tax['tax_amount']
            bases.add(tax['base_code_id'])
            bases.add(tax['ref_base_code_id'])
            taxes.add(tax['tax_code_id'])
            taxes.add(tax['ref_tax_code_id'])
            if tax['tax_type'] == 'purchase':
                purchases.add(tax['tax_id'])




        """
        basecodeinfo = {}
        for tc in taxcodes:
            ref = tc['ref_base_code_id']
            reftc = tc['ref_tax_code_id']
            tcid = tc['base_code_id']
            tctc = tc['tax_code_id']
            for baseid in ref, reftc, tcid, tctc:
                if baseid and not baseid in basecodeinfo:
                    basecodeinfo[baseid] = {'refbase' : [], 'reftc' : [], 'base' : [], 'tc' : []}

            basecodeinfo[baseid]['refbase'].append(ref)
            basecodeinfo[baseid]['reftc'].append(reftc)
            basecodeinfo[baseid]['base'].append(tcid)
            basecodeinfo[baseid]['tc'].append(tctc)
        """

        # Gjedna


        period_list = self.period_ids
        if not period_list:
            self.cr.execute ("select id from account_fiscalyear")
            fy = self.cr.fetchall()
            self.cr.execute ("select id from account_period where fiscalyear_id = %s",(fy[0][0],))
            periods = self.cr.fetchall()
            for p in periods:
                period_list.append(p[0])

        total_amount = 0.0
        total_amount_reporting = 0.0
        tax_to_pay = 0.0
        tax_to_pay_reporting = 0.0
        total_amount_vatable = 0.0
        total_amount_vatable_reporting = 0.0


        self.cr.execute("""select line.ref, line.name, line.tax_amount, line.tax_amount_in_reporting_currency,
        line.debit, line.debit_in_reporting_currency, line.credit, line.credit_in_reporting_currency, account.code,
        tc.name as taxcodename, tc.position_in_tax_report, line.account_tax_id, line.tax_code_id
            from account_move_line line
            left outer join account_account account on account.id=line.account_id
            ---left outer join account_tax tax on tax.id=line.account_tax_id
            left outer join account_tax_code tc on tc.id=line.tax_code_id
             """)
        tcinfo = self.cr.dictfetchall()

        postsum = []
        for i in range(len(TAX_REPORT_STRINGS)):
            postsum.append([0.0, 0.0, 0.0, 0.0])

        for tc in tcinfo:
            """ line.ref, line.name, line.debit, line.credit, account.code,
            tax.name as taxname, tc.name as taxcodename, tc.position_in_tax_report,
            line.account_tax_id """
            zum = tc['credit'] - tc['debit']
            amt = tc['tax_amount']
            amt_rep = tc['tax_amount_in_reporting_currency']
            debcred = tc['credit'] - tc['debit']
            debcred_rep = tc['credit_in_reporting_currency'] - tc['debit_in_reporting_currency']

            pos = tc['position_in_tax_report']
            tcname = tc['taxcodename']
            taxid = tc['account_tax_id']
            codeid = tc['tax_code_id']
            if not pos:
                continue

            factor = self.get_sign(signs, codeid)

            if codeid in bases: # This is a base
                postsum[pos][0] += amt
                postsum[pos][2] += amt_rep
                if taxid and not taxid in purchases:
                    total_amount += factor * amt
                    total_amount_reporting += factor * amt_rep
                    if not codeid in exempt:
                        total_amount_vatable += factor * amt
                        total_amount_vatable_reporting += factor * amt_rep
            else:
                postsum[pos][1] += amt
                postsum[pos][3] += amt_rep
                tax_to_pay += factor * amt
                tax_to_pay_reporting += factor * amt_rep


        for post_number in range(2, len(postsum)-1):
            percentage = 25 # NOT USED
            tax_use = 'yes'
            res_dict = {'code' : post_number,
                        'name' : TAX_REPORT_STRINGS[post_number],
                        'tax_base' : postsum[post_number][0],
                        'tax_amount' : postsum[post_number][1],
                        'tax_base_reporting' : postsum[post_number][2],
                        'tax_amount_reporting' : postsum[post_number][3],
                        'percentage' : percentage,
                        'tax_use' : tax_use}
            lines.append(res_dict)


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






    def X_get_lines(self, based_on, company_id=False, parent=False, level=0, context=None):
        # Get the base codes
        self.cr.execute('select tax.position_in_tax_report as post, tax.name as taxname, tax.type, tax.amount, tax.type_tax_use, '
                                ' btc.id as base_id, btc.code as base_code, btc.name as basetaxcodename, '
                                ' tc.id as tax_id, tc.code as tax_code, btc.name as taxcodename '
                                'from account_tax tax '
                                'left outer join account_tax_code btc on tax.base_code_id=btc.id '
                                'left outer join account_tax_code tc on tax.tax_code_id=tc.id '
                                'order by position_in_tax_report'
        )
        #self.cr.execute('select tax.name as taxname, tax.type, tax.amount, tax.type_tax_use '
        #                        'from account_tax tax '
        #                        'order by tax.amount desc, tax.type_tax_use'
        #)



        basecodes =  self.cr.dictfetchall()
        period_list = self.period_ids
        if not period_list:
            self.cr.execute ("select id from account_fiscalyear")
            fy = self.cr.fetchall()
            self.cr.execute ("select id from account_period where fiscalyear_id = %s",(fy[0][0],))
            periods = self.cr.fetchall()
            for p in periods:
                period_list.append(p[0])


        # MÅ FIKSE SLIK AT BASE CODE ER FORSKJELLIG!
        base_amounts = {}
        lines = []

        total_amount = 0.0
        total_amount_reporting = 0.0
        tax_to_pay = 0.0
        tax_to_pay_reporting = 0.0
        total_amount_vatable = 0.0
        total_amount_vatable_reporting = 0.0

        for post_number in range(3, len(TAX_REPORT_STRINGS)-1):
            self.cr.execute('select tax.position_in_tax_report as post, tax.name as taxname, tax.type, tax.amount, tax.type_tax_use, '
                                ' btc.id as base_id, btc.code as base_code, btc.name as basetaxcodename, '
                                ' tc.id as tax_id, tc.code as tax_code, btc.name as taxcodename '
                                'from account_tax tax '
                                'left outer join account_tax_code btc on tax.base_code_id=btc.id '
                                'left outer join account_tax_code tc on tax.tax_code_id=tc.id '
                                'where position_in_tax_report=%d' % post_number)
            if self.cr.rowcount:
                codeinfo = self.cr.dictfetchall()[0]
            else:
                codeinfo = None


            print "CODEINFO", codeinfo

            res_baseamount = res_amount = None
            if codeinfo:
                res_baseamount = self._get_amount(codeinfo['base_id'], period_list, company_id, based_on, context=context)
                res_amount = self._get_amount(codeinfo['tax_id'], period_list, company_id, based_on, context=context)
                print "CODEINFO", codeinfo['type_tax_use'], '--', codeinfo['type_tax_use'] == 'sale', codeinfo['type_tax_use'] == 'purchase'
                #if codeinfo['type_tax_use'] == 'sale':
                #    #direction = 'credit'
                #    sign = 1.0
                #else:
                #    #direction = 'debit'
                #    #sign = -1.0

            if not res_baseamount:
                tax_base_amount = tax_amount = 0.0
                tax_base_reporting = tax_amount_reporting = 0.0
                percentage = None
                tax_use = None
            else:
                print "TAX NAME", codeinfo['taxname'], 'tax amounts',\
                ' '.join(repr([x['credit'] for x in res_amount] )),\
                ' '.join(repr([x['debit'] for x in res_amount] ) )
                tax_base_amount = sum([ x['credit'] for x in res_baseamount ]) - \
                                    sum([ x['debit'] for x in res_baseamount ])
                tax_amount = sum([x['credit'] for x in res_amount]) - \
                        sum([x['debit'] for x in res_amount])
                tax_base_reporting = sum([x['credit_reporting'] for x in res_baseamount]) - \
                        sum([x['debit_reporting'] for x in res_baseamount])
                tax_amount_reporting = sum([x['credit_reporting'] for x in res_amount]) - \
                            sum([x['debit_reporting'] for x in res_amount])
                percentage = codeinfo['amount'] * 100
                tax_use = codeinfo['type_tax_use']
                if percentage>0.0:
                    total_amount_vatable += tax_base_amount
                    total_amount_vatable_reporting += tax_base_reporting

            #if sign > 0:
            #    total_amount += tax_base_amount
            #    total_amount_reporting += tax_base_reporting
            # hmm
            tax_to_pay += tax_amount
            tax_to_pay_reporting += tax_amount_reporting

            res_dict = {'code' : post_number,
                        'name' : TAX_REPORT_STRINGS[post_number],
                        'tax_base' : tax_base_amount,
                        'tax_amount' : tax_amount,
                        'tax_base_reporting' : tax_base_reporting,
                        'tax_amount_reporting' : tax_amount_reporting,
                        'percentage' : percentage,
                        'tax_use' : tax_use}
            print "RES_DICT", res_dict
            #base_amounts.append( (codeinfo['tax_use'], codeinfo['amount'], res_baseamount['tax_amount'] )  )
            #res_general = self._get_general(codeinfo['id'], period_list, company_id, based_on, context=context)
            lines.append(res_dict)

        # The sum code
        res_dict = {'code' : 1,
                        'name' : TAX_REPORT_STRINGS[1],
                        'tax_base' : total_amount,
                        'tax_amount' : None,
                        'tax_base_reporting' : total_amount_reporting,
                        'tax_amount_reporting' : None,
                        'percentage' : None,
                        'tax_use' : codeinfo['type_tax_use']}
        lines.insert(0, res_dict)

        res_dict = {'code' : 2,
                        'name' : TAX_REPORT_STRINGS[2],
                        'tax_base' : total_amount_vatable,
                        'tax_amount' : None,
                        'tax_base_reporting' : total_amount_vatable_reporting,
                        'tax_amount_reporting' : None,
                        'percentage' : None,
                        'tax_use' : codeinfo['type_tax_use']}
        lines.insert(1, res_dict)


        if tax_to_pay > 0.0:
            name = TAX_REPORT_STRINGS[11][0]
        else:
            name = TAX_REPORT_STRINGS[11][1]

        res_dict = {'code' : 11,
                        'name' : name,
                        'tax_base' : None,
                        'tax_amount' : tax_to_pay,
                        'tax_base_reporting' : None,
                        'tax_amount_reporting' : tax_to_pay_reporting,
                        'percentage' : None,
                        'tax_use' : codeinfo['type_tax_use']}
        lines.append(res_dict)


        # Check that all are there




        return lines

        """
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
        """

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
