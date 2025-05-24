import datetime

from parse import Transaction


class TestIsSplit:
    def test_non_split(self):
        trans = Transaction(
            datetime.datetime.now(),
            'Some Merchant',
            1.11,
            0,
            'Normal transaction, nothing to see here'
        )

        is_split, is_first = trans.is_split()

        assert is_split is False
        assert is_first is False

    def test_split_first_of_sequence(self):
        trans = Transaction(
            datetime.datetime.now(),
            'Some Merchant',
            1.11,
            0,
            'Split (1/17)'
        )

        is_split, is_first = trans.is_split()

        assert is_split is True
        assert is_first is True

    def test_split_not_first_of_sequence(self):
        trans = Transaction(
            datetime.datetime.now(),
            'Some Merchant',
            1.11,
            0,
            'Split (12/17)'
        )

        is_split, is_first = trans.is_split()

        assert is_split is True
        assert is_first is False

    def test_split_with_additional_memo(self):
        trans = Transaction(
            datetime.datetime.now(),
            'Some Merchant',
            1.11,
            0,
            'Stuff and things -- Split (1/2)'
        )

        is_split, is_first = trans.is_split()

        assert is_split is True
        assert is_first is True
