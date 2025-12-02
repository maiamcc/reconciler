#!/usr/bin/env python

from parse import parse_csv, ImportType
from reconcile import reconcile

# TODO: arg parser
YNAB_CSV_PATH = './ynab.csv'
CITI_CSV_PATH = './citi.csv'


def main():
    ynab_transactions = parse_csv(YNAB_CSV_PATH, ImportType.YNAB)
    citi_transactions = parse_csv(CITI_CSV_PATH, ImportType.CITI)

    reconcile(citi_transactions, ynab_transactions)


if __name__ == '__main__':
    main()
