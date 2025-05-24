import csv
from dataclasses import dataclass
from enum import Enum

import datetime
from typing import Callable, Optional, List
import re


class ImportType(Enum):
    YNAB = 1
    CITI = 2
    # other banks I use go here I guess


YNAB_DATE_FMTSTR = '%m/%d/%Y'
CITI_DATE_FMTSTR = '%m/%d/%Y'


@dataclass
class Transaction:
    """The details I care about of a transaction."""
    date: datetime.datetime
    payee: str
    inflow: float
    outflow: float
    notes: Optional[str]

    def is_split(self) -> (bool, bool):
        """Is it a YNAB split transaction?
        Returns:
            - is_split (bool): is this transaction part of a split?
            - is_beginning_of_split (bool): is this the FIRST transaction of a split?
        """
        match = re.match('.*Split \((\d+)\/\d+\).*', self.notes)
        if not match:
            return False, False

        return True, match.group(1) == '1'

    def amt(self) -> float:
        if self.inflow:
            return self.inflow
        return -self.outflow

    def datestr(self) -> str:
        return self.date.strftime(YNAB_DATE_FMTSTR)

    def __str__(self) -> str:
        cash_str = f'+${self.inflow}' if self.inflow else f'-${self.outflow}'
        s = f'{self.datestr()} | {self.payee} | {cash_str}'
        if self.notes:
            s += f' | {self.notes}'
        return s

    @staticmethod
    def list_to_string(transactions: List['Transaction']) -> str:
        return '\t' + '\n\t'.join([trans.__str__() for trans in transactions])


def parse_dollar(dollarstr: str) -> float:
    return float(re.sub(r'[^\d.]', '', dollarstr))


def parse_ynab(path: str) -> List[Transaction]:
    transactions = []
    with open(path) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                transactions.append(
                    Transaction(
                        datetime.datetime.strptime(row['Date'], YNAB_DATE_FMTSTR),
                        row['Payee'],
                        parse_dollar(row['Inflow']),
                        parse_dollar(row['Outflow']),
                        row['Memo']
                    )
                )
            except Exception as e:
                print(f'!!! done goofed parsing row:\n\t{row}')
                raise e

    return _normalize_ynab_splits(transactions)


def _collapse_transactions(transactions: List[Transaction]) -> Transaction:
    """Given a list of transactions, smush them into one."""
    if not transactions:
        raise ValueError('No transactions passed!')

    if len({trans.date for trans in transactions}) != 1:
        raise ValueError(f'Can\'t collapse transactions with different dates! {transactions}')

    collapsed_payee = ' / '.join({trans.payee for trans in transactions})
    total_inflow = sum([trans.inflow for trans in transactions])
    total_outflow = sum([trans.outflow for trans in transactions])

    return Transaction(
        transactions[0].date,
        collapsed_payee,
        total_inflow,
        total_outflow,
        f'Collapsed from {len(transactions)} transactions'
    )


def _normalize_ynab_splits(transactions: List[Transaction]) -> List[Transaction]:
    """
    YNAB will write a split transaction as two separate rows, but for reconciliation
    purposes I want a single row (because that's how it'll show up in my bank statement).

    Assume split transactions will be adjacent in the list and contain the memo "Split (x/y)",
    otherwise we're in real trouble.
    """
    normalized = []
    current_split = []  # accumulate transactions belonging to a single split

    for trans in transactions:
        is_split, is_beginning_of_split = trans.is_split()
        if not is_split:
            if current_split:
                # we've reached the end of the current split we're evaluating, resolve it
                normalized.append(_collapse_transactions(current_split))
                current_split = []
            normalized.append(trans)
        else:
            if is_beginning_of_split and current_split:
                # reached the end of the current split, resolve it
                normalized.append(_collapse_transactions(current_split))
                current_split = []
            current_split.append(trans)

    # if the last transaction was part of a split, handle that split
    if current_split:
        normalized.append(_collapse_transactions(current_split))

    return normalized


def parse_citi(path: str) -> List[Transaction]:
    transactions = []
    with open(path) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                transactions.append(
                    Transaction(
                        datetime.datetime.strptime(row['Date'], CITI_DATE_FMTSTR),
                        row['Description'],
                        abs(float(row['Credit'])) if row['Credit'] else 0,
                        float(row['Debit']) if row['Debit'] else 0,
                        None
                    )
                )
            except Exception as e:
                print(f'!!! done goofed parsing row:\n\t{row}')
                raise e

    return transactions


PARSE_FUNCS: dict[ImportType, Callable[[str], List[Transaction]]] = {
    ImportType.YNAB: parse_ynab,
    ImportType.CITI: parse_citi,
}


def parse_csv(path: str, typ: ImportType) -> List[Transaction]:
    parse_func = PARSE_FUNCS.get(typ)
    if not parse_func:
        raise Exception(f'Unrecognized type: {typ}')

    return parse_func(path)
