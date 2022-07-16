from uuid import UUID
from decimal import Decimal
from eventsourcing.application import Application, AggregateNotFound

from bankaccounts.aggregate import BankAccount
from bankaccounts.exceptions import *


class BankAccounts(Application):
    def open_account(self, full_name: str, email_address: str) -> UUID:
        account = BankAccount.open(
            full_name=full_name,
            email_address=email_address,
        )
        self.save(account)
        return account.id

    def get_account(self, account_id: UUID) -> BankAccount:
        try:
            aggregate = self.repository.get(account_id)
        except AggregateNotFound:
            raise AccountNotFoundError(account_id)
        else:
            assert isinstance(aggregate, BankAccount)
            return aggregate

    def get_balance(self, account_id: UUID) -> Decimal:
        account = self.get_account(account_id)
        return account.balance

    def deposit_funds(self, credit_account_id: UUID, amount: Decimal) -> None:
        account = self.get_account(credit_account_id)
        account.append_transaction(amount)
        self.save(account)

    def withdraw_funds(self, debit_account_id: UUID, amount: Decimal) -> None:
        account = self.get_account(debit_account_id)
        account.append_transaction(-amount)
        self.save(account)

    def transfer_funds(
        self,
        debit_account_id: UUID,
        credit_account_id: UUID,
        amount: Decimal,
    ) -> None:
        debit_account = self.get_account(debit_account_id)
        credit_account = self.get_account(credit_account_id)
        debit_account.append_transaction(-amount)
        credit_account.append_transaction(amount)
        self.save(debit_account, credit_account)

    def set_overdraft_limit(self, account_id: UUID, overdraft_limit: Decimal) -> None:
        account = self.get_account(account_id)
        account.set_overdraft_limit(overdraft_limit)
        self.save(account)

    def get_overdraft_limit(self, account_id: UUID) -> Decimal:
        account = self.get_account(account_id)
        return account.overdraft_limit

    def close_account(self, account_id: UUID) -> None:
        account = self.get_account(account_id)
        account.close()
        self.save(account)

from functools import singledispatchmethod
from logging import getLogger
from eventsourcing.system import ProcessApplication, ProcessingEvent
from eventsourcing.domain import AggregateEvent
from bankaccounts.aggregate import Opened, Closed, AccountsOpened, AccountsClosed

class Reports(ProcessApplication):
    @singledispatchmethod
    def policy(self, domain_event: AggregateEvent, processing_event: ProcessingEvent):
        pass
        # self._log_info("Opened: %s", domain_event)

    @policy.register(Opened)
    def _(self, domain_event: Opened, processing_event: ProcessingEvent):
        self._log_info("Opened: %s", domain_event)

        accounts_opened = self.get_accounts_opened()
        accounts_opened.increment_count(1)
        processing_event.collect_events(accounts_opened)

    @policy.register(Closed)
    def _(self, domain_event: Opened, processing_event: ProcessingEvent):
        self._log_info("Closed: %s", domain_event)

        accounts_opened = self.get_accounts_opened()
        accounts_closed = self.get_accounts_closed()

        accounts_opened.decrement_count(1)
        accounts_closed.increment_count(1)

        processing_event.collect_events(accounts_opened, accounts_closed)

    def get_accounts_opened(self) -> AccountsOpened:
        try:
            accounts_opened = self.repository.get(AccountsOpened.create_id())
        except AggregateNotFound:
            accounts_opened = AccountsOpened(count=0)
            self.save(accounts_opened)

        return accounts_opened

    def get_accounts_closed(self) -> AccountsClosed:
        try:
            accounts_closed = self.repository.get(AccountsClosed.create_id())
        except AggregateNotFound:
            accounts_closed = AccountsClosed(count=0)
            accounts_closed_id = self.save(accounts_closed)
            assert accounts_closed_id

        return accounts_closed

    def _log_info(self, message, *args, **kwargs):
        getLogger().info(message, *args, **kwargs)

