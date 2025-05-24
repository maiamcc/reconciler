#! /bin/env python

from parse import parse_csv, ImportType
# TODO: arg parser
YNAB_CSV_PATH = './ynab.csv'
CITI_CARD_CSV_PATH = './citi_card.csv'


def main():
    ynab_transactions = parse_csv(YNAB_CSV_PATH, ImportType.YNAB)
    citi_transactions = parse_csv(CITI_CARD_CSV_PATH, ImportType.CITI)

    



if __name__ == '__main__':
    main()
