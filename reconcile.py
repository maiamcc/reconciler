import datetime
from typing import List, Dict
from collections import defaultdict, namedtuple

from tabulate import tabulate

import parse
from parse import Transaction


def _bucket_by_month(transactions: List[Transaction]) -> Dict[datetime.datetime, List[Transaction]]:
    bucketed = defaultdict(list)
    for trans in transactions:
        bucketed[trans.date.replace(day=1)].append(trans)
    return bucketed


InOutTransactionList = namedtuple('InOutTransactionList', ['in_list', 'out_list'])


def _bucket_by_amount(transactions: List[Transaction]) -> InOutTransactionList:
    in_out_transactions = InOutTransactionList(defaultdict(list), defaultdict(list))
    for trans in transactions:
        if trans.inflow and trans.outflow:
            raise ValueError(f'Unexpected state: one transaction with both inflow and outflow! {trans}')

        if trans.inflow:
            in_out_transactions.in_list[trans.inflow].append(trans)
        else:
            in_out_transactions.out_list[trans.outflow].append(trans)
    return in_out_transactions


def reconcile(source_transactions: List[Transaction], ynab_transactions: List[Transaction]) -> List[Transaction]:
    source_transactions_by_month = _bucket_by_month(source_transactions)
    ynab_transactions_by_month = _bucket_by_month(ynab_transactions)

    unclaimed_source_transactions = []
    unclaimed_ynab_transactions = []

    # if source_transactions_by_month.keys() != ynab_transactions_by_month.keys():
    #     raise ValueError('Mismatched months, somehow?!')
    for month, ynab_for_month in ynab_transactions_by_month.items():
        source_for_month = source_transactions_by_month[month]

        month_total_source = sum([txn.inflow - txn.outflow for txn in source_for_month])
        month_total_ynab = sum([txn.inflow - txn.outflow for txn in ynab_for_month])

        unclaimed_source, unclaimed_ynab = _reconcile_month(source_for_month, ynab_for_month)

        unclaimed_source_transactions.extend(unclaimed_source)
        unclaimed_ynab_transactions.extend(unclaimed_ynab)
        print(f'successfully reconciled month {month.strftime(parse.YNAB_DATE_FMTSTR)}')
        print(f'-- Source total: {month_total_source}')
        print(f'-- YNAB total: {month_total_ynab}')
        if month_total_ynab != month_total_source:
            print(f'---- DIFFERENCE: {month_total_ynab - month_total_source}')

    extra_months_in_source = set(source_transactions_by_month.keys()) - (ynab_transactions_by_month.keys())
    print('-----')
    if extra_months_in_source:
        print(f'Months found in source and not in YNAB: {", ".join([mo.strftime(parse.YNAB_DATE_FMTSTR) for mo in extra_months_in_source])}')
    if unclaimed_source_transactions:
        unclaimed_source_transactions = sorted(unclaimed_source_transactions, key=lambda t: (t.date, t.amt()))
        print(f'Unclaimed source transactions:\n{Transaction.list_to_string(unclaimed_source_transactions)}')
    if unclaimed_ynab_transactions:
        unclaimed_ynab_transactions = sorted(unclaimed_ynab_transactions, key=lambda t: (t.date, t.amt()))
        print(f'Unclaimed ynab transactions:\n{Transaction.list_to_string(unclaimed_ynab_transactions)}')


def _reconcile_month(source_transactions: List[Transaction], ynab_transactions: List[Transaction]) -> (List[Transaction], List[Transaction]):
    source_by_amount = _bucket_by_amount(source_transactions)
    ynab_by_amount = _bucket_by_amount(ynab_transactions)

    unclaimed_source_transactions = []
    unclaimed_ynab_transactions = []

    matched_months_table = []
    for amt, source_trans in source_by_amount.in_list.items():
        ynab_trans = ynab_by_amount.in_list[amt]
        if len(source_trans) == len(ynab_trans):
            matched_months_table.append(
                [Transaction.list_to_string(source_trans), Transaction.list_to_string(ynab_trans)]
            )
        else:
            unclaimed_source_transactions.extend(source_trans)
            unclaimed_ynab_transactions.extend(ynab_trans)


    for amt, source_trans in source_by_amount.out_list.items():
        ynab_trans = ynab_by_amount.out_list[amt]
        if len(source_trans) == len(ynab_trans):
            pass
        else:
            unclaimed_source_transactions.extend(source_trans)
            unclaimed_ynab_transactions.extend(ynab_trans)

    extra_inflow_amts_in_ynab = set(ynab_by_amount.in_list.keys()) - (source_by_amount.in_list.keys())
    for extra_amt in extra_inflow_amts_in_ynab:
        unclaimed_ynab_transactions.extend(ynab_by_amount.in_list[extra_amt])

    extra_outflow_amts_in_ynab = set(ynab_by_amount.out_list.keys()) - (source_by_amount.out_list.keys())
    for extra_amt in extra_outflow_amts_in_ynab:
        unclaimed_ynab_transactions.extend(ynab_by_amount.out_list[extra_amt])

    print(tabulate(matched_months_table))

    return unclaimed_source_transactions, unclaimed_ynab_transactions
