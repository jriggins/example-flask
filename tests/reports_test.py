from unittest import TestCase, main

from bankaccounts.application import BankAccounts, Reports
from bankaccounts.aggregate import BankAccount, AccountsOpened, AccountsClosed
from eventsourcing.system import System, SingleThreadedRunner

class TestReports(TestCase):
    def setUp(self):
        self.system = System([[BankAccounts, Reports]])
        self.runner = SingleThreadedRunner(self.system)
        self.runner.start()
        self.bank_accounts = self.runner.get(BankAccounts)
        self.reports = self.runner.get(Reports)

    def tearDown(self):
        self.runner and self.runner.stop()

    def test_account_opened(self):
        self.assertIsNotNone(self.reports)

        for i in range(10):
            account_id = self.bank_accounts.open_account(f"Test User{i}", f"test{i}@example.com")
            account: BankAccount = self.bank_accounts.get_account(account_id)
            self.assertFalse(account.is_closed)

        account_opened_report = self.reports.get_accounts_opened()
        self.assertIsNotNone(self.reports.repository.get(AccountsOpened.create_id()))
        self.assertEqual(10, account_opened_report.count)

        account_closed_report = self.reports.get_accounts_closed()
        self.assertEqual(0, account_closed_report.count)

    def test_account_closed(self):
        self.assertIsNotNone(self.reports)

        account_ids = []
        for i in range(10):
            account_id = self.bank_accounts.open_account(f"Test User{i}", f"test{i}@example.com")
            account: BankAccount = self.bank_accounts.get_account(account_id)
            self.assertFalse(account.is_closed)
            account_ids.append(account_id)

        self.bank_accounts.close_account(account_ids[-1])

        account_opened_report = self.reports.get_accounts_opened()
        self.assertEqual(9, account_opened_report.count)

        account_closed_report = self.reports.get_accounts_closed()
        self.assertEqual(1, account_closed_report.count)
        self.assertIsNotNone(self.reports.repository.get(AccountsClosed.create_id()))

    def test_lots(self):
        account_ids = []

        count = 3_000

        print(f"Creating {count} accounts")
        for i in range(count):
            account_id = self.bank_accounts.open_account(f"Test User{i}", f"test{i}@example.com")
            # account: BankAccount = self.bank_accounts.get_account(account_id)
            # self.assertFalse(account.is_closed)
            account_ids.append(account_id)
        print(f"Done Creating {count} accounts")

        print(f"Getting number open accounts")
        account_opened_report = self.reports.get_accounts_opened()
        self.assertEqual(count, account_opened_report.count)

if __name__ == '__main__':
    main()
