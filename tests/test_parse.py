import datetime
from decimal import Decimal

import pytest

from parse import Transaction, _collapse_transactions, _normalize_ynab_splits


def _date_from_str(datestr: str) -> datetime.datetime:
    return datetime.datetime.strptime(datestr, '%m/%d/%Y')


def test_transaction(date='01/01/2000', payee='Some Merchant', inflow: Decimal = 0, outflow: Decimal = 0, notes=''):
    return Transaction(_date_from_str(date), payee, inflow, outflow, notes)


class TestIsSplit:
    def test_non_split(self):
        trans = test_transaction(notes='Normal transaction, nothing to see here')

        is_split, is_beginning_of_split = trans.is_split()

        assert is_split is False
        assert is_beginning_of_split is False

    def test_split_first_of_sequence(self):
        trans = test_transaction(notes='Split (1/17)')

        is_split, is_beginning_of_split = trans.is_split()

        assert is_split is True
        assert is_beginning_of_split is True

    def test_split_not_first_of_sequence(self):
        trans = test_transaction(notes='Split (12/17)')

        is_split, is_beginning_of_split = trans.is_split()

        assert is_split is True
        assert is_beginning_of_split is False

    def test_split_with_additional_memo(self):
        trans = test_transaction(notes='Stuff and things -- Split (1/2)')

        is_split, is_beginning_of_split = trans.is_split()

        assert is_split is True
        assert is_beginning_of_split is True


class TestCollapseTransactions:
    def test_collapse(self):
        transactions = [
            test_transaction(date='04/20/1969', payee='Some Merchant', inflow=Decimal(0), outflow=Decimal('1.11')),
            test_transaction(date='04/20/1969', payee='Some Merchant', inflow=Decimal(0), outflow=Decimal('2.22')),
            test_transaction(date='04/20/1969', payee='Some Merchant', inflow=Decimal(0), outflow=Decimal('3.33')),
        ]

        collapsed = _collapse_transactions(transactions)

        assert collapsed.date == _date_from_str('4/20/1969')
        assert collapsed.payee == 'Some Merchant'
        assert collapsed.inflow == 0
        assert collapsed.outflow == Decimal('6.66')
        assert '3 transactions' in collapsed.notes

    def test_collapse_inflow(self):
        transactions = [
            test_transaction(date='04/20/1969', payee='Some Merchant', inflow=Decimal('1.11'), outflow=Decimal(0)),
            test_transaction(date='04/20/1969', payee='Some Merchant', inflow=Decimal('2.22'), outflow=Decimal(0)),
            test_transaction(date='04/20/1969', payee='Some Merchant', inflow=Decimal('3.33'), outflow=Decimal(0)),
        ]

        collapsed = _collapse_transactions(transactions)

        assert collapsed.date == _date_from_str('4/20/1969')
        assert collapsed.payee == 'Some Merchant'
        assert collapsed.inflow == Decimal('6.66')
        assert collapsed.outflow == 0
        assert '3 transactions' in collapsed.notes

    def test_multiple_payees(self):
        transactions = [
            test_transaction(date='04/20/1969', payee='FooCo.', outflow=Decimal('1.11')),
            test_transaction(date='04/20/1969', payee='Bar Shop', outflow=Decimal('2.22')),
        ]

        collapsed = _collapse_transactions(transactions)

        assert collapsed.date == _date_from_str('4/20/1969')
        assert 'FooCo.' in collapsed.payee
        assert 'Bar Shop' in collapsed.payee
        assert collapsed.inflow == 0
        assert collapsed.outflow == Decimal('3.33')
        assert '2 transactions' in collapsed.notes

    def test_multiple_dates_throws_error(self):
        transactions = [
            test_transaction(date='04/20/2040', payee='FooCo.', outflow=Decimal('1.11')),
            test_transaction(date='04/20/1969', payee='Bar Shop', outflow=Decimal('2.22'))
        ]

        with pytest.raises(ValueError):
            _collapse_transactions(transactions)


class TestNormalizeYnabSplits:
    def test_noop(self):
        transactions = [
            test_transaction(date='04/20/1969', payee='Foo', outflow=Decimal('1.11')),
            test_transaction(date='04/21/1969', payee='Bar', outflow=Decimal('2.22')),
            test_transaction(date='04/22/1969', payee='Baz', inflow=Decimal('3.33'))
        ]

        normalized = _normalize_ynab_splits(transactions)

        assert normalized == transactions  # no-op: nothing should have changed

    def test_normalize_splits(self):
        transactions = [
            test_transaction(date='04/20/1969', payee='Foo', outflow=Decimal('1.11')),
            test_transaction(date='04/21/1969', payee='Bar', outflow=Decimal('2.22'), notes='Split (1/2)'),
            test_transaction(date='04/21/1969', payee='Bar', outflow=Decimal('0.44'), notes='Split (2/2)'),
            test_transaction(date='04/22/1969', payee='Baz', inflow=Decimal('3.33')),
            test_transaction(date='04/23/1969', payee='Beep', inflow=Decimal('0.01'), notes='Split (1/3)'),
            test_transaction(date='04/23/1969', payee='Beep', inflow=Decimal('0.02'), notes='Split (2/3)'),
            test_transaction(date='04/23/1969', payee='Beep', inflow=Decimal('0.03'), notes='Split (3/3)'),
            test_transaction(date='04/24/1969', payee='Quux', outflow=Decimal('123')),
        ]

        normalized = _normalize_ynab_splits(transactions)

        assert len(normalized) == 5
        assert {trans.payee for trans in normalized} == {'Foo', 'Bar', 'Baz', 'Beep', 'Quux'}

    def test_normalize_trailing_split(self):
        transactions = [
            test_transaction(date='04/20/1969', payee='Foo', outflow=Decimal('1.11')),
            test_transaction(date='04/21/1969', payee='Bar', outflow=Decimal('2.22'), notes='Split (1/2)'),
            test_transaction(date='04/21/1969', payee='Bar', outflow=Decimal('0.44'), notes='Split (2/2)'),
            test_transaction(date='04/22/1969', payee='Baz', inflow=Decimal('3.33')),
            test_transaction(date='04/23/1969', payee='Beep', inflow=Decimal('0.01'), notes='Split (1/3)'),
            test_transaction(date='04/23/1969', payee='Beep', inflow=Decimal('0.02'), notes='Split (2/3)'),
            test_transaction(date='04/23/1969', payee='Beep', inflow=Decimal('0.03'), notes='Split (3/3)'),
        ]

        normalized = _normalize_ynab_splits(transactions)

        assert len(normalized) == 4
        assert {trans.payee for trans in normalized} == {'Foo', 'Bar', 'Baz', 'Beep'}

    def test_normalize_adjacent_splits(self):
        transactions = [
            test_transaction(date='04/20/1969', payee='Foo', outflow=Decimal(1.11)),
            test_transaction(date='04/21/1969', payee='Bar', outflow=Decimal(2.22), notes='Split (1/2)'),
            test_transaction(date='04/21/1969', payee='Bar', outflow=Decimal(0.44), notes='Split (2/2)'),
            test_transaction(date='04/23/1969', payee='Beep', inflow=Decimal(0.01), notes='Split (1/3)'),
            test_transaction(date='04/23/1969', payee='Beep', inflow=Decimal(0.02), notes='Split (2/3)'),
            test_transaction(date='04/23/1969', payee='Beep', inflow=Decimal(0.03), notes='Split (3/3)'),
            test_transaction(date='04/24/1969', payee='Quux', outflow=Decimal(123)),
        ]

        normalized = _normalize_ynab_splits(transactions)

        assert len(normalized) == 4
        assert {trans.payee for trans in normalized} == {'Foo', 'Bar', 'Beep', 'Quux'}
