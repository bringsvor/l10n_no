# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013 ZedeS Technologies, zedestech.com
#    Copyright (C) 2013 Datalege AS, www.datalege.no
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Norway - Accounting',
    'version': '1.0',
    'author': 'Tinderbox AS and Bringsvor Consulting AS',
    'website': 'http://www.tinderbox.no',
    'category': 'Localization/Account Charts',
    'description': """
Norway - VAT report
==================================
Standard kontoplan NS 4102
""",
    'depends': ['base_iban', 'base_vat','account_chart','account'],
    'data': [
                #'account_tax_code.xml',
                #'l10n_no_chart.xml',
                #'account_tax.xml',
                #'vat_report.py',
                'views/report_vat.xml',
                #'views/account_tax_code.xml',
                'account_report.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}

