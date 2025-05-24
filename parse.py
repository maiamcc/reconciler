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


@dataclass
class Transaction:
    """The details I care about of a transaction."""
    date: datetime.datetime
    payee: str
    inflow: float
    outflow: float
    notes: Optional[str]

    def is_split(self) -> bool:
        """Is it a YNAB split transaction?"""
        return re.match('.*Split \(\d+\/\d+\).*', self.notes) is not None


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
                print('!!! done goofed parsing row:\n\t{row}')
                raise e

    return _normalize_ynab_splits(transactions)


def _collapse_transactions(transactions: List[Transaction]) -> Transaction:
    """Given a list of transactions, smush them into one."""

    # Hopefully they have the same date and merchant. If not uh,
    # cross that bridge when we come to it?
    if len({trans.date for trans in transactions}) != 1:
        raise ValueError(f'Can\'t collapse transactions with different dates! {transactions}')

    collapsed_payee = ' / '.join({trans.payee for trans in transactions})
    total_inflow = sum([trans.inflow for trans in transactions])
    total_outflow = sum([trans.inflow for trans in transactions])

    return Transaction(
        transactions[0].date,
        transactions[0].payee,
        total_inflow,
        total_outflow,
        f'Collapsed from {len(transactions)} transactions'
    )

def _normalize_ynab_splits(transactions: List[Transaction]) -> List[Transaction]:
    """
    YNAB will write a split transaction as two separate rows, but for reconciliation
    purposes I want a single row (because that's how it'll show up in my bank statement).

    Assume split transactions will be adjacent in the list and contain the meme "Split (x/y)",
    otherwise we're in real trouble.
    """
    normalized = []
    current_split = []  # accumulate transactions belonging to a single split

    for trans in transactions:
        if not trans.is_split():
            if current_split:
                # we've reached the end of the current split we're evaluating, resolve it
                normalized.append(_collapse_transactions(current_split))
                current_split = []
            normalized.append(trans)
        else:
            current_split.append(trans)

    # if the last transaction was part of a split, handle that split
    if current_split:
        normalized.append(_collapse_transactions(current_split))

    return normalized

def parse_citi(path: str) -> List[Transaction]:
    pass


PARSE_FUNCS: dict[ImportType, Callable[[str], List[Transaction]]] = {
    ImportType.YNAB: parse_ynab,
    ImportType.CITI: parse_citi,
}


def parse_csv(path: str, typ: ImportType) -> List[Transaction]:
    parse_func = PARSE_FUNCS.get(typ)
    if not parse_func:
        raise Exception(f'Unrecognized type: {typ}')

    return parse_func(path)
